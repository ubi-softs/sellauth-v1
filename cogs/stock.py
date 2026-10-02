import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from utils.checks import is_staff
from utils.embeds import make_embed
from utils.sellauth import SellAuthError, stock_rows, unwrap

log = logging.getLogger("sellauth-bot.stock")


class Stock(commands.GroupCog, name="stock"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._alerted: set = set()
        super().__init__()

    async def cog_load(self):
        if config.LOW_STOCK_CHANNEL_ID:
            self.watch.start()

    async def cog_unload(self):
        self.watch.cancel()

    @app_commands.command(name="check", description="Check stock (all products, or one product)")
    @app_commands.describe(product_id="Optional product ID")
    @is_staff()
    async def check(self, interaction: discord.Interaction, product_id: Optional[str] = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if product_id:
            products = [unwrap(await self.bot.sellauth.get_product(product_id))]
        else:
            products = await self.bot.sellauth.all_products()

        rows = [r for p in products for r in stock_rows(p) if r[1] is not None]
        rows.sort(key=lambda r: r[1])
        if not rows:
            return await interaction.followup.send(embed=make_embed("Stock", "No limited-stock items found."))

        def icon(n: int) -> str:
            return "🔴" if n == 0 else "🟡" if n <= config.LOW_STOCK_THRESHOLD else "🟢"

        lines = [f"{icon(n)} **{label}**: {n}" for label, n, _ in rows[:30]]
        embed = make_embed("Stock (lowest first)", "\n".join(lines))
        embed.set_footer(text=f"Low = {config.LOW_STOCK_THRESHOLD} or fewer | showing {min(len(rows), 30)}/{len(rows)}")
        await interaction.followup.send(embed=embed)

    @tasks.loop(minutes=config.LOW_STOCK_INTERVAL_MIN)
    async def watch(self):
        try:
            channel = self.bot.get_channel(config.LOW_STOCK_CHANNEL_ID) or await self.bot.fetch_channel(
                config.LOW_STOCK_CHANNEL_ID
            )
            products = await self.bot.sellauth.all_products()
            low = {}
            for p in products:
                for label, stock, vid in stock_rows(p):
                    if stock is not None and stock <= config.LOW_STOCK_THRESHOLD:
                        low[(p.get("id"), vid)] = (label, stock)
            new = {k: v for k, v in low.items() if k not in self._alerted}
            self._alerted = set(low)  # items that recovered get re-alerted next time they drop
            if new:
                lines = [f"{'🔴' if s == 0 else '🟡'} **{label}**: {s}" for label, s in new.values()][:30]
                await channel.send(embed=make_embed("Low stock alert", "\n".join(lines)))
        except SellAuthError as e:
            log.warning("Stock watch API error: %s", e.message)
        except Exception:
            log.exception("Stock watch failed")

    @watch.before_loop
    async def before_watch(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Stock(bot))

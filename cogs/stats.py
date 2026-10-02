import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed
from utils.sellauth import as_list, money, pick, scalars, unwrap


def describe(item: dict) -> str:
    return " | ".join(f"{k}: {v}" for k, v in scalars(item, depth=0)[:4])[:150]


class Stats(commands.GroupCog, name="stats"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="overview", description="Revenue and shop stats")
    @is_staff()
    async def overview(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        data = unwrap(await self.bot.sellauth.analytics())
        embed = make_embed("Shop overview")
        fields = scalars(data)[:24] if isinstance(data, dict) else []
        for name, value in fields:
            embed.add_field(name=name, value=value)
        if not fields:
            embed.description = "The API returned no simple stats."
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="top-products", description="Best selling products")
    @is_staff()
    async def top_products(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        items = as_list(await self.bot.sellauth.top_products())[:10]
        if not items:
            return await interaction.followup.send(embed=make_embed("Top products", "No data yet."))
        lines = []
        for i, p in enumerate(items, 1):
            name = pick(p, "product_name", "name")
            if name == "N/A":
                lines.append(f"{i}. {describe(p)}")
                continue
            rev = money(pick(p, "total_revenue_usd", "revenue_usd", "total", default=0))
            orders = pick(p, "total_orders", "orders", default="?")
            lines.append(f"{i}. **{name}** - {rev} ({orders} orders)")
        await interaction.followup.send(embed=make_embed("Top products", "\n".join(lines)))

    @app_commands.command(name="top-customers", description="Biggest spenders")
    @is_staff()
    async def top_customers(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        items = as_list(await self.bot.sellauth.top_customers())[:10]
        if not items:
            return await interaction.followup.send(embed=make_embed("Top customers", "No data yet."))
        lines = []
        for i, c in enumerate(items, 1):
            email = pick(c, "email", "customer_email")
            if email == "N/A":
                lines.append(f"{i}. {describe(c)}")
                continue
            spent = money(pick(c, "total_spent_usd", "total_revenue_usd", "total", default=0))
            orders = pick(c, "total_orders", "orders", default="?")
            lines.append(f"{i}. **{email}** - {spent} ({orders} orders)")
        await interaction.followup.send(embed=make_embed("Top customers", "\n".join(lines)))


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))

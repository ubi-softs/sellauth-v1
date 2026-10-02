from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed, success_embed
from utils.sellauth import as_list, page_text, pick
from utils.views import confirm


class Coupons(commands.GroupCog, name="coupons"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="list", description="List coupons")
    @is_staff()
    async def list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True, thinking=True)
        data = await self.bot.sellauth.list_coupons(page)
        coupons = as_list(data)
        if not coupons:
            return await interaction.followup.send(embed=make_embed("Coupons", "No coupons found."))
        lines = []
        for c in coupons:
            unit = "%" if pick(c, "type") == "percentage" else " USD"
            lines.append(
                f"`{pick(c, 'id')}` **{pick(c, 'code')}** - {pick(c, 'discount')}{unit} "
                f"| uses {pick(c, 'uses', default=0)}/{pick(c, 'max_uses', default='inf')}"
            )
        embed = make_embed("Coupons", "\n".join(lines))
        embed.set_footer(text=page_text(data, page))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="create", description="Create a coupon")
    @app_commands.describe(
        code="Coupon code",
        discount="Discount amount (percent or fixed)",
        discount_type="Percentage or fixed amount",
        global_coupon="Works on every product (default yes)",
        items="Product IDs, comma separated (required if not global)",
        max_uses="Max total uses",
        max_uses_per_customer="Max uses per customer",
        min_invoice_price="Minimum order price",
        expires="Expiry date, YYYY-MM-DD",
    )
    @app_commands.rename(discount_type="type", global_coupon="global")
    @app_commands.choices(
        discount_type=[
            app_commands.Choice(name="Percentage", value="percentage"),
            app_commands.Choice(name="Fixed amount", value="fixed"),
        ]
    )
    @is_staff()
    async def create(
        self,
        interaction: discord.Interaction,
        code: str,
        discount: float,
        discount_type: app_commands.Choice[str],
        global_coupon: bool = True,
        items: Optional[str] = None,
        max_uses: Optional[int] = None,
        max_uses_per_customer: Optional[int] = None,
        min_invoice_price: Optional[float] = None,
        expires: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not global_coupon and not items:
            raise app_commands.CheckFailure("Not-global coupons need `items` (product IDs).")
        payload = {
            "code": code,
            "global": global_coupon,
            "discount": discount,
            "type": discount_type.value,
            "disable_if_volume_discount": False,
        }
        if items:
            payload["items"] = [i.strip() for i in items.split(",") if i.strip()]
        if max_uses:
            payload["max_uses"] = max_uses
        if max_uses_per_customer:
            payload["max_uses_per_customer"] = max_uses_per_customer
        if min_invoice_price is not None:
            payload["min_invoice_price"] = min_invoice_price
        if expires:
            payload["expiration_date"] = expires
        await self.bot.sellauth.create_coupon(payload)
        unit = "%" if discount_type.value == "percentage" else " USD"
        await interaction.followup.send(embed=success_embed(f"Coupon `{code}` created: {discount}{unit} off."))

    @app_commands.command(name="delete", description="Delete a coupon")
    @app_commands.describe(coupon_id="Coupon ID from /coupons list")
    @is_staff()
    async def delete(self, interaction: discord.Interaction, coupon_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await confirm(interaction, f"Delete coupon `{coupon_id}`?"):
            return await interaction.followup.send("Cancelled.", ephemeral=True)
        await self.bot.sellauth.delete_coupon(coupon_id)
        await interaction.followup.send(embed=success_embed(f"Coupon `{coupon_id}` deleted."), ephemeral=True)

    @app_commands.command(name="clear-used", description="Delete all used-up coupons")
    @is_staff()
    async def clear_used(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await confirm(interaction, "Delete ALL used coupons?"):
            return await interaction.followup.send("Cancelled.", ephemeral=True)
        await self.bot.sellauth.delete_used_coupons()
        await interaction.followup.send(embed=success_embed("Used coupons deleted."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Coupons(bot))

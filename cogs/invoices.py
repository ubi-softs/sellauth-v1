from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed, success_embed
from utils.sellauth import as_list, money, page_text, pick, unwrap
from utils.views import confirm


def item_label(it: dict) -> str:
    prod = it.get("product") if isinstance(it.get("product"), dict) else {}
    var = it.get("variant") if isinstance(it.get("variant"), dict) else {}
    name = pick(it, "product_name", default=None) or prod.get("name") or "Item"
    vname = pick(it, "variant_name", default=None) or var.get("name")
    qty = pick(it, "quantity", default=1)
    return f"{qty}x {name}" + (f" ({vname})" if vname else "")


class Orders(commands.GroupCog, name="order"):
    """Orders are 'invoices' in SellAuth."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="list", description="List recent orders")
    @app_commands.describe(email="Filter by customer email", status="Filter by status (e.g. completed)", page="Page")
    @is_staff()
    async def list(
        self,
        interaction: discord.Interaction,
        email: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        filters = {"email": email, "statuses": [status] if status else None}
        data = await self.bot.sellauth.list_invoices(page, **filters)
        invoices = as_list(data)
        if not invoices:
            return await interaction.followup.send(embed=make_embed("Orders", "No orders found."))
        lines = [
            f"`{pick(i, 'id')}` | {pick(i, 'email', 'customer_email')} | "
            f"{money(pick(i, 'price_usd', 'total', 'amount'))} | {pick(i, 'status')}"
            for i in invoices
        ]
        embed = make_embed("Orders", "\n".join(lines))
        embed.set_footer(text=page_text(data, page))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="info", description="Show an order")
    @app_commands.describe(invoice_id="Order / invoice ID")
    @is_staff()
    async def info(self, interaction: discord.Interaction, invoice_id: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        inv = unwrap(await self.bot.sellauth.get_invoice(invoice_id))
        embed = make_embed(f"Order {pick(inv, 'id', default=invoice_id)}")
        embed.add_field(name="Email", value=str(pick(inv, "email", "customer_email")))
        embed.add_field(name="Status", value=str(pick(inv, "status")))
        embed.add_field(name="Gateway", value=str(pick(inv, "gateway", "payment_method")))
        embed.add_field(name="Price", value=money(pick(inv, "price_usd", "total", "amount")))
        embed.add_field(name="Paid", value=money(pick(inv, "paid_usd", default=0)))
        embed.add_field(name="Coupon", value=str(pick(inv, "coupon_code", default="none")))
        embed.add_field(name="Created", value=str(pick(inv, "created_at"))[:19])
        embed.add_field(name="Completed", value=str(pick(inv, "completed_at"))[:19])
        items = inv.get("items") or inv.get("invoice_items") or []
        if items:
            embed.add_field(name="Items", value="\n".join(item_label(i) for i in items[:10]), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="refund", description="Mark an order as refunded")
    @is_staff()
    async def refund(self, interaction: discord.Interaction, invoice_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await confirm(interaction, f"Refund order `{invoice_id}`?"):
            return await interaction.followup.send("Cancelled.", ephemeral=True)
        await self.bot.sellauth.refund_invoice(invoice_id)
        await interaction.followup.send(embed=success_embed(f"Order `{invoice_id}` refunded."), ephemeral=True)

    @app_commands.command(name="cancel", description="Cancel an order")
    @is_staff()
    async def cancel(self, interaction: discord.Interaction, invoice_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await confirm(interaction, f"Cancel order `{invoice_id}`?"):
            return await interaction.followup.send("Cancelled.", ephemeral=True)
        await self.bot.sellauth.cancel_invoice(invoice_id)
        await interaction.followup.send(embed=success_embed(f"Order `{invoice_id}` cancelled."), ephemeral=True)

    @app_commands.command(name="resend", description="Re-process an order (re-deliver the product)")
    @is_staff()
    async def resend(self, interaction: discord.Interaction, invoice_id: str):
        await interaction.response.defer(ephemeral=True)
        await self.bot.sellauth.process_invoice(invoice_id)
        await interaction.followup.send(embed=success_embed(f"Order `{invoice_id}` re-processed."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Orders(bot))

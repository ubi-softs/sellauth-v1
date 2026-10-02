import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed
from utils.sellauth import pick, unwrap


class Invoices(commands.GroupCog, name="invoices"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="list", description="List recent invoices")
    @app_commands.describe(page="Page number")
    @is_staff()
    async def list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True, thinking=True)
        invoices = unwrap(await self.bot.sellauth.list_invoices(page))
        if not invoices:
            return await interaction.followup.send(embed=make_embed("Invoices", "No invoices found."))

        lines = [
            f"`{pick(i, 'id')}` | {pick(i, 'email', 'customer_email')} | {pick(i, 'status')}"
            for i in invoices[:20]
        ]
        await interaction.followup.send(embed=make_embed(f"Invoices (page {page})", "\n".join(lines)))

    @app_commands.command(name="info", description="Show details for an invoice")
    @app_commands.describe(invoice_id="The invoice ID")
    @is_staff()
    async def info(self, interaction: discord.Interaction, invoice_id: int):
        await interaction.response.defer(ephemeral=True, thinking=True)
        inv = unwrap(await self.bot.sellauth.get_invoice(invoice_id))
        embed = make_embed(f"Invoice {pick(inv, 'id', default=invoice_id)}")
        embed.add_field(name="Email", value=str(pick(inv, "email", "customer_email")))
        embed.add_field(name="Status", value=str(pick(inv, "status")))
        embed.add_field(name="Gateway", value=str(pick(inv, "gateway", "payment_method")))
        embed.add_field(name="Created", value=str(pick(inv, "created_at")))
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Invoices(bot))

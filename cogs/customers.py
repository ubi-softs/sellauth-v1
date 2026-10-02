import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed
from utils.sellauth import as_list, money, pick


class Customers(commands.GroupCog, name="customer"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="lookup", description="Look up a customer and their recent orders by email")
    @app_commands.describe(email="Customer email")
    @is_staff()
    async def lookup(self, interaction: discord.Interaction, email: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        customers = as_list(await self.bot.sellauth.list_customers(email=email))
        invoices = as_list(await self.bot.sellauth.list_invoices(1, 8, email=email))
        if not customers and not invoices:
            return await interaction.followup.send(embed=make_embed("Customer", f"Nothing found for `{email}`."))

        embed = make_embed(f"Customer: {email}")
        if customers:
            c = customers[0]
            embed.add_field(name="Customer ID", value=str(pick(c, "id")))
            embed.add_field(name="Balance", value=money(pick(c, "balance", default=0)))
            embed.add_field(name="Joined", value=str(pick(c, "created_at"))[:10])
        if invoices:
            lines = [
                f"`{pick(i, 'id')}` | {money(pick(i, 'price_usd', 'total', 'amount'))} | {pick(i, 'status')}"
                for i in invoices
            ]
            embed.add_field(name="Recent orders", value="\n".join(lines), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Customers(bot))

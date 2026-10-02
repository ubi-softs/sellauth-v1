import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed
from utils.sellauth import pick, unwrap


class Shop(commands.GroupCog, name="shop"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="info", description="Show your SellAuth shop info")
    @is_staff()
    async def info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        shop = unwrap(await self.bot.sellauth.get_shop())
        embed = make_embed(str(pick(shop, "name", default="Shop")))
        embed.add_field(name="ID", value=str(pick(shop, "id")))
        embed.add_field(name="Subdomain", value=str(pick(shop, "subdomain")))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stats", description="Show your shop statistics")
    @is_staff()
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        stats = unwrap(await self.bot.sellauth.get_stats())
        embed = make_embed("Shop Stats")
        if isinstance(stats, dict):
            for key, value in stats.items():
                if isinstance(value, (str, int, float)):
                    embed.add_field(name=key.replace("_", " ").title(), value=str(value))
        if not embed.fields:
            embed.description = "No simple stats returned by the API."
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))

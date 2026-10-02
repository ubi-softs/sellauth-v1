from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_owner
from utils.embeds import make_embed, success_embed


def _cog_names() -> list[str]:
    return [f.stem for f in Path("cogs").glob("*.py") if not f.name.startswith("_")]


class Admin(commands.GroupCog, name="admin"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=n, value=n)
            for n in _cog_names()
            if current.lower() in n.lower()
        ][:25]

    @app_commands.command(name="reload", description="Reload a cog without restarting")
    @app_commands.autocomplete(cog=cog_autocomplete)
    @is_owner()
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(f"cogs.{cog}")
        await interaction.followup.send(embed=success_embed(f"Reloaded `{cog}`."))

    @app_commands.command(name="sync", description="Re-sync slash commands")
    @is_owner()
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
        else:
            synced = await self.bot.tree.sync()
        await interaction.followup.send(embed=success_embed(f"Synced {len(synced)} commands."))

    @app_commands.command(name="cogs", description="List loaded cogs")
    @is_owner()
    async def cogs(self, interaction: discord.Interaction):
        loaded = ", ".join(f"`{c}`" for c in self.bot.cogs)
        await interaction.response.send_message(embed=make_embed("Loaded Cogs", loaded), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))

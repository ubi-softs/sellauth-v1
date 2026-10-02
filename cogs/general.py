import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import make_embed


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=make_embed("Pong!", f"Latency: `{round(self.bot.latency * 1000)}ms`")
        )

    @app_commands.command(name="help", description="List all commands")
    async def help(self, interaction: discord.Interaction):
        embed = make_embed("Commands")
        for cmd in self.bot.tree.get_commands():
            if isinstance(cmd, app_commands.Group):
                subs = ", ".join(f"`/{cmd.name} {c.name}`" for c in cmd.commands)
                embed.add_field(name=cmd.name.title(), value=subs or "-", inline=False)
            else:
                embed.add_field(name=f"/{cmd.name}", value=cmd.description, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))

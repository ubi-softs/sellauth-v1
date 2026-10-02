from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed, success_embed
from utils.sellauth import as_list, page_text, pick
from utils.views import confirm


class Blacklist(commands.GroupCog, name="blacklist"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="list", description="Show blacklist entries")
    @is_staff()
    async def list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True, thinking=True)
        data = await self.bot.sellauth.list_blacklist(page)
        entries = as_list(data)
        if not entries:
            return await interaction.followup.send(embed=make_embed("Blacklist", "No entries."))
        lines = [f"`{pick(b, 'id')}` {pick(b, 'type')}: **{pick(b, 'value')}**" for b in entries]
        embed = make_embed("Blacklist", "\n".join(lines))
        embed.set_footer(text=page_text(data, page))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="add", description="Blacklist an email, IP, Discord ID, etc.")
    @app_commands.describe(type="email, ip, discord_id, ...", value="The value to block", reason="Optional reason")
    @is_staff()
    async def add(self, interaction: discord.Interaction, type: str, value: str, reason: Optional[str] = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        payload = {"type": type, "match_type": "exact", "value": value}
        if reason:
            payload["reason"] = reason
        await self.bot.sellauth.add_blacklist(payload)
        await interaction.followup.send(embed=success_embed(f"Blacklisted `{type}`: `{value}`"))

    @app_commands.command(name="remove", description="Remove a blacklist entry")
    @app_commands.describe(entry_id="ID from /blacklist list")
    @is_staff()
    async def remove(self, interaction: discord.Interaction, entry_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await confirm(interaction, f"Remove blacklist entry `{entry_id}`?"):
            return await interaction.followup.send("Cancelled.", ephemeral=True)
        await self.bot.sellauth.delete_blacklist(entry_id)
        await interaction.followup.send(embed=success_embed(f"Entry `{entry_id}` removed."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))

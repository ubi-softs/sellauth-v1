import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import config
from utils.embeds import error_embed
from utils.sellauth import SellAuthClient, SellAuthError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
log = logging.getLogger("sellauth-bot")


class SellAuthBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
            help_command=None,
        )
        self.sellauth = SellAuthClient(config.SELLAUTH_API_KEY, config.SELLAUTH_SHOP_ID)

    async def setup_hook(self) -> None:
        # Auto-load every file in /cogs (skips files starting with "_")
        for file in sorted(Path("cogs").glob("*.py")):
            if file.name.startswith("_"):
                continue
            ext = f"cogs.{file.stem}"
            try:
                await self.load_extension(ext)
                log.info("Loaded %s", ext)
            except Exception:
                log.exception("Failed to load %s", ext)

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

        self.tree.error(self.on_tree_error)

    async def on_ready(self) -> None:
        log.info("Logged in as %s (%s)", self.user, self.user.id)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="your shop"))

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        original = getattr(error, "original", error)
        if isinstance(error, app_commands.CheckFailure):
            msg = str(error) or "You can't use this command."
        elif isinstance(original, SellAuthError):
            msg = f"SellAuth API error ({original.status}): {original.message}"
        else:
            log.exception("Unhandled command error", exc_info=error)
            msg = "Something went wrong. Check the console logs."

        embed = error_embed(msg)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def close(self) -> None:
        await self.sellauth.close()
        await super().close()


def main() -> None:
    missing = [n for n in ("DISCORD_TOKEN", "SELLAUTH_API_KEY", "SELLAUTH_SHOP_ID") if not getattr(config, n)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    SellAuthBot().run(config.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()

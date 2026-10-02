import discord

import config


def make_embed(title: str, description: str | None = None, color: int = config.EMBED_COLOR) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="SellAuth Bot")
    return embed


def success_embed(message: str) -> discord.Embed:
    return make_embed("Success", message, config.SUCCESS_COLOR)


def error_embed(message: str) -> discord.Embed:
    return make_embed("Error", message, config.ERROR_COLOR)

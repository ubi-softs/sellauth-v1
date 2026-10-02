import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed
from utils.sellauth import pick, unwrap


class Products(commands.GroupCog, name="products"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="list", description="List your products")
    @app_commands.describe(page="Page number")
    @is_staff()
    async def list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True, thinking=True)
        products = unwrap(await self.bot.sellauth.list_products(page))
        if not products:
            return await interaction.followup.send(embed=make_embed("Products", "No products found."))

        lines = [f"`{pick(p, 'id')}` | **{pick(p, 'name')}**" for p in products[:20]]
        embed = make_embed(f"Products (page {page})", "\n".join(lines))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="info", description="Show details for a product")
    @app_commands.describe(product_id="The product ID")
    @is_staff()
    async def info(self, interaction: discord.Interaction, product_id: int):
        await interaction.response.defer(ephemeral=True, thinking=True)
        product = unwrap(await self.bot.sellauth.get_product(product_id))
        embed = make_embed(str(pick(product, "name", default=f"Product {product_id}")))
        desc = pick(product, "description", default="")
        if desc:
            embed.description = str(desc)[:1000]
        embed.add_field(name="ID", value=str(pick(product, "id")))
        embed.add_field(name="Visibility", value=str(pick(product, "visibility")))

        variants = product.get("variants") or []
        if variants:
            vlines = [
                f"{pick(v, 'name')} - {pick(v, 'price')} (stock: {pick(v, 'stock_count', 'stock')})"
                for v in variants[:10]
            ]
            embed.add_field(name="Variants", value="\n".join(vlines), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Products(bot))

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_staff
from utils.embeds import make_embed, success_embed
from utils.sellauth import as_list, money, page_text, pick, unwrap
from utils.views import confirm


class Products(commands.GroupCog, name="products"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="list", description="List your products")
    @is_staff()
    async def list(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer(ephemeral=True, thinking=True)
        data = await self.bot.sellauth.list_products(page)
        products = as_list(data)
        if not products:
            return await interaction.followup.send(embed=make_embed("Products", "No products found."))
        lines = [f"`{pick(p, 'id')}` | **{pick(p, 'name')}** | {pick(p, 'visibility')}" for p in products]
        embed = make_embed("Products", "\n".join(lines))
        embed.set_footer(text=page_text(data, page))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="info", description="Show product details")
    @is_staff()
    async def info(self, interaction: discord.Interaction, product_id: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        p = unwrap(await self.bot.sellauth.get_product(product_id))
        embed = make_embed(str(pick(p, "name", default=f"Product {product_id}")))
        desc = pick(p, "description", default="")
        if desc:
            embed.description = str(desc)[:1000]
        embed.add_field(name="ID", value=str(pick(p, "id")))
        embed.add_field(name="Type", value=str(pick(p, "type")))
        embed.add_field(name="Visibility", value=str(pick(p, "visibility")))
        variants = p.get("variants") or []
        if variants:
            vlines = [
                f"`{pick(v, 'id')}` {pick(v, 'name')} - {money(pick(v, 'price'))} "
                f"(stock: {pick(v, 'stock_count', 'stock', default='unlimited')})"
                for v in variants[:10]
            ]
            embed.add_field(name="Variants", value="\n".join(vlines), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="create", description="Create a product with one variant")
    @app_commands.describe(name="Product name", price="Price in USD", description="Description", visibility="public or hidden")
    @app_commands.choices(
        product_type=[
            app_commands.Choice(name="Serials (stock list)", value="serials"),
            app_commands.Choice(name="Service", value="service"),
            app_commands.Choice(name="Dynamic", value="dynamic"),
        ]
    )
    @app_commands.rename(product_type="type")
    @is_staff()
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        price: float,
        product_type: app_commands.Choice[str],
        description: str = "",
        visibility: str = "public",
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        # VERIFY: payload shape. SellAuth products are built from variants.
        payload = {
            "name": name,
            "description": description,
            "visibility": visibility,
            "type": product_type.value,
            "variants": [{"name": "Default", "price": price}],
        }
        data = unwrap(await self.bot.sellauth.create_product(payload))
        pid = pick(data, "id", default="?") if isinstance(data, dict) else "?"
        await interaction.followup.send(embed=success_embed(f"Product **{name}** created (ID `{pid}`)."))

    @app_commands.command(name="edit", description="Edit a product (only filled fields change)")
    @app_commands.describe(product_id="Product ID", name="New name", description="New description", visibility="New visibility")
    @is_staff()
    async def edit(
        self,
        interaction: discord.Interaction,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        visibility: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        payload = {k: v for k, v in {"name": name, "description": description, "visibility": visibility}.items() if v}
        if not payload:
            raise app_commands.CheckFailure("Fill in at least one field to change.")
        await self.bot.sellauth.update_product(product_id, payload)
        await interaction.followup.send(embed=success_embed(f"Product `{product_id}` updated."))

    @app_commands.command(name="clone", description="Duplicate a product")
    @is_staff()
    async def clone(self, interaction: discord.Interaction, product_id: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.sellauth.clone_product(product_id)
        await interaction.followup.send(embed=success_embed(f"Product `{product_id}` cloned."))

    @app_commands.command(name="delete", description="Delete a product")
    @is_staff()
    async def delete(self, interaction: discord.Interaction, product_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await confirm(interaction, f"Delete product `{product_id}`? This can't be undone."):
            return await interaction.followup.send("Cancelled.", ephemeral=True)
        await self.bot.sellauth.delete_product(product_id)
        await interaction.followup.send(embed=success_embed(f"Product `{product_id}` deleted."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Products(bot))

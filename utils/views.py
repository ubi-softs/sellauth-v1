import discord


class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.value: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your confirmation.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


async def confirm(interaction: discord.Interaction, text: str) -> bool:
    """Ask for confirmation with buttons. The interaction must already be deferred."""
    view = ConfirmView(interaction.user.id)
    msg = await interaction.followup.send(f"⚠️ {text}", view=view, ephemeral=True, wait=True)
    await view.wait()
    for child in view.children:
        child.disabled = True
    try:
        await msg.edit(view=view)
    except discord.HTTPException:
        pass
    return bool(view.value)

from discord import Interaction, app_commands

import config


def is_staff():
    """Allow only users listed in OWNER_IDS or STAFF_IDS (.env)."""

    async def predicate(interaction: Interaction) -> bool:
        uid = interaction.user.id
        if uid in config.OWNER_IDS or uid in config.STAFF_IDS:
            return True
        raise app_commands.CheckFailure("You don't have permission to use this command.")

    return app_commands.check(predicate)


def is_owner():
    async def predicate(interaction: Interaction) -> bool:
        if interaction.user.id in config.OWNER_IDS:
            return True
        raise app_commands.CheckFailure("Owner only command.")

    return app_commands.check(predicate)

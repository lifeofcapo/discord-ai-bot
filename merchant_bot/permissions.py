import discord
from discord import app_commands

from .config import ADMIN_COMMAND_ROLES


def has_admin_role(role_names: set[str]) -> bool:
    return bool(role_names.intersection(ADMIN_COMMAND_ROLES))


def is_authorized_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        role_names = {r.name for r in interaction.user.roles}
        return has_admin_role(role_names)
    return app_commands.check(predicate)
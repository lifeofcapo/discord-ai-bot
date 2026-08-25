import discord
from discord import app_commands

from .config import ADMIN_COMMAND_ROLES


def has_admin_role(role_names: set[str]) -> bool:
    """
    Чистая функция без зависимости от discord.py — легко тестируется напрямую,
    без необходимости мокать Interaction/Member.
    """
    return bool(role_names.intersection(ADMIN_COMMAND_ROLES))


def is_authorized_admin():
    """
    Декоратор для admin-команд. Проверяет роль по ИМЕНИ (Technical Administrator,
    Mentor, The Standard), а не системное право Discord "Administrator" —
    так можно управлять доступом ролями, не трогая права каждого человека вручную.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        role_names = {r.name for r in interaction.user.roles}
        return has_admin_role(role_names)
    return app_commands.check(predicate)
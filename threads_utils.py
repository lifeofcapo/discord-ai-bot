import discord

from config import STAFF_ROLE_NAMES


async def create_private_thread(
    interaction: discord.Interaction,
    thread_name: str,
) -> discord.Thread:
    """
    Создаёт приватный тред в канале, где произошло взаимодействие.
    Автор добавляется явно. Staff видит тред автоматически через право
    "Управление ветками" (Manage Threads), которое должно быть выдано
    ролям Mentor/Founder на уровне категории.
    """
    channel = interaction.channel

    thread = await channel.create_thread(
        name=thread_name,
        type=discord.ChannelType.private_thread,
        invitable=False,  # обычные участники не могут сами приглашать друг друга
    )

    await thread.add_user(interaction.user)

    return thread


def is_staff(member: discord.Member) -> bool:
    """Проверка, является ли участник Authorized Staff."""
    member_role_names = {role.name for role in member.roles}
    return bool(member_role_names.intersection(STAFF_ROLE_NAMES))
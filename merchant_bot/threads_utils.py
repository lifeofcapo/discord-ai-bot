import discord

from .config import STAFF_ROLE_NAMES


async def create_private_thread(
    interaction: discord.Interaction,
    thread_name: str,
) -> discord.Thread:
    channel = interaction.channel

    thread = await channel.create_thread(
        name=thread_name,
        type=discord.ChannelType.private_thread,
        invitable=False,
    )

    await thread.add_user(interaction.user)

    guild = interaction.guild
    staff_roles = [r for r in guild.roles if r.name in STAFF_ROLE_NAMES]
    for role in staff_roles:
        for member in role.members:
            if member.id == interaction.user.id:
                continue  
            try:
                await thread.add_user(member)
            except discord.HTTPException:
                pass  

    return thread


def is_staff(member: discord.Member) -> bool:
    member_role_names = {role.name for role in member.roles}
    return bool(member_role_names.intersection(STAFF_ROLE_NAMES))
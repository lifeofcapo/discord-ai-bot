import discord
from discord.ext import commands

from ..config import BLOCKED_REACTIONS


class ReactionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) not in BLOCKED_REACTIONS:
            return
        if payload.user_id == self.bot.user.id:
            return

        channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(payload.user_id)

        try:
            await message.remove_reaction(payload.emoji, user)
        except discord.HTTPException:
            pass  # реакция уже могла быть убрана вручную — не критично


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionsCog(bot))
import logging
import time

import discord
from discord.ext import commands

from ..config import SUPPORT_CENTER_CHANNEL

log = logging.getLogger("merchant-bot")

# не чаще раза в час одному и тому же человеку — чтобы не заспамить,
# если он пишет боту в личку несколько сообщений подряд
DM_AUTOREPLY_COOLDOWN_SECONDS = 60 * 60

_last_reply_at: dict[int, float] = {}


class DMAutoReplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channel_mention: str | None = None 

    def _find_support_channel_mention(self) -> str:
        if self._channel_mention:
            return self._channel_mention

        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=SUPPORT_CENTER_CHANNEL)
            if channel:
                self._channel_mention = channel.mention
                return self._channel_mention

        log.warning(
            f"I haven't found'{SUPPORT_CENTER_CHANNEL}'"
            "automessage was sent without link to channel"
        )
        return "support channel on a server"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return

        now = time.monotonic()
        last = _last_reply_at.get(message.author.id, 0)
        if now - last < DM_AUTOREPLY_COOLDOWN_SECONDS:
            return
        _last_reply_at[message.author.id] = now

        channel_hint = self._find_support_channel_mention()

        try:
            await message.channel.send(
                "👋 Hi! I'm not responsing here.\n"
                f"To ask a question, go to {channel_hint} on a server and press it "
                "«🎫 Open Private Support Ticket» — this faster."
            )
        except discord.HTTPException:
            log.exception(f"Не удалось отправить автоответ на ЛС от {message.author.id}")


async def setup(bot: commands.Bot):
    await bot.add_cog(DMAutoReplyCog(bot))
import os
import logging
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import set_key

from ..config import SERVER_STATS_CATEGORY_NAME, SERVER_STATS_CHANNEL_NAME_TEMPLATE

log = logging.getLogger("merchant-bot")

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class ServerStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.category_id: int | None = self._get_env_int("SERVER_STATS_CATEGORY_ID")
        self.channel_id: int | None = self._get_env_int("SERVER_STATS_CHANNEL_ID")
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @staticmethod
    def _get_env_int(name: str) -> int | None:
        value = os.getenv(name)
        return int(value) if value else None

    def _persist_id(self, name: str, value: int):
        os.environ[name] = str(value)
        try:
            set_key(str(ENV_PATH), name, str(value))
            log.info(f"{name}={value} сохранён в .env")
        except Exception:
            log.exception(
                f"Не удалось автоматически сохранить {name} в .env — "
                f"добавь вручную строку: {name}={value}"
            )

    async def _get_or_create_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        if self.category_id:
            category = guild.get_channel(self.category_id)
            if isinstance(category, discord.CategoryChannel):
                return category
            log.warning(
                f"SERVER_STATS_CATEGORY_ID={self.category_id} задан, но категория "
                "с таким ID не найдена на сервере — создаю новую"
            )

        category = await guild.create_category(
            SERVER_STATS_CATEGORY_NAME,
            position=0,  # сразу наверх
            reason="Автосоздание категории для статистики сервера",
        )
        self.category_id = category.id
        self._persist_id("SERVER_STATS_CATEGORY_ID", category.id)
        return category

    async def _get_or_create_channel(self, guild: discord.Guild) -> discord.VoiceChannel:
        if self.channel_id:
            channel = guild.get_channel(self.channel_id)
            if isinstance(channel, discord.VoiceChannel):
                return channel
            log.warning(
                f"SERVER_STATS_CHANNEL_ID={self.channel_id} задан, но канал "
                "с таким ID не найден на сервере — создаю новый"
            )

        category = await self._get_or_create_category(guild)
        channel = await guild.create_voice_channel(
            SERVER_STATS_CHANNEL_NAME_TEMPLATE.format(count=guild.member_count),
            category=category,
            position=0,  # сразу наверх внутри категории
            overwrites={
                # видно всем, зайти нельзя — это чисто "счётчик"
                guild.default_role: discord.PermissionOverwrite(
                    connect=False, view_channel=True
                )
            },
            reason="Автосоздание канала со статистикой сервера",
        )
        self.channel_id = channel.id
        self._persist_id("SERVER_STATS_CHANNEL_ID", channel.id)
        return channel

    @tasks.loop(minutes=10)
    async def update_stats(self):
        guild = self.bot.get_guild(self.bot.guild_id)
        if guild is None:
            return

        channel = await self._get_or_create_channel(guild)

        new_name = SERVER_STATS_CHANNEL_NAME_TEMPLATE.format(count=guild.member_count)
        if channel.name == new_name:
            return

        try:
            await channel.edit(name=new_name)
        except discord.HTTPException:
            log.exception("Не удалось обновить название канала со статистикой")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerStatsCog(bot))
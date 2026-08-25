import logging

import discord
from discord import app_commands
from discord.ext import commands

from .. import state
from ..ai_client import get_ai_response, build_user_content

log = logging.getLogger("merchant-bot")


class AIAssistantCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        thread_id = message.channel.id

        # Отвечаем только там, где реально запущено AI-пространство
        if not state.is_ai_thread(thread_id):
            return

        image_urls = [
            att.url for att in message.attachments
            if att.content_type and att.content_type.startswith("image/")
        ]

        user_content = build_user_content(message.content, image_urls)
        state.append_message(thread_id, "user", user_content)

        async with message.channel.typing():
            try:
                reply = await get_ai_response(state.get_history(thread_id))
            except Exception as e:
                log.error(f"OpenAI error: {e}")
                await message.channel.send(
                    "⚠️ Something went wrong while generating a response. Please try again in a moment."
                )
                return

        state.append_message(thread_id, "assistant", reply)
        await message.channel.send(reply)

    @app_commands.command(
        name="reset",
        description="Сбросить память и историю в этом AI-пространстве",
    )
    async def reset(self, interaction: discord.Interaction):
        thread_id = interaction.channel.id

        if not state.is_ai_thread(thread_id):
            await interaction.response.send_message(
                "Эта команда работает только внутри приватного AI-пространства.",
                ephemeral=True,
            )
            return

        state.reset_thread(thread_id)
        await interaction.response.send_message("🔄 Память сброшена. Можно начинать с чистого листа.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIAssistantCog(bot))
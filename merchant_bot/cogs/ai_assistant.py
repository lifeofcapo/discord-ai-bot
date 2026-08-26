import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..ai_client import get_ai_response, build_user_content
from ..db import repository as db
from .. import knowledge_base as kb
from .. import storage

log = logging.getLogger("merchant-bot")


class AIAssistantCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        thread_id = message.channel.id

        if not await db.is_ai_thread(thread_id):
            return

        image_urls = []
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                image_urls.append(att.url)
                # Сохраняем копию в S3 — Discord-ссылка временная и рано или поздно протухнет
                try:
                    await storage.save_screenshot(message.author.id, att.url, att.content_type)
                except Exception as e:
                    log.error(f"Screenshot upload failed: {e}")

        user_content = build_user_content(message.content, image_urls)
        await db.append_message(thread_id, "user", user_content)

        async with message.channel.typing():
            try:
                # RAG: подтягиваем релевантные куски базы знаний под конкретное сообщение
                kb_entries = await kb.search(message.content or "sales conversation analysis")
                kb_context = kb.format_for_prompt(kb_entries)

                history = await db.get_history(thread_id)
                if kb_context:
                    history = [{"role": "system", "content": kb_context}] + history

                reply = await get_ai_response(history)
            except Exception as e:
                log.error(f"OpenAI error: {e}")
                await message.channel.send(
                    "⚠️ Something went wrong while generating a response. Please try again in a moment."
                )
                return

        await db.append_message(thread_id, "assistant", reply)
        await message.channel.send(reply)

    @app_commands.command(name="reset", description="Сбросить память и историю в этом AI-пространстве")
    async def reset(self, interaction: discord.Interaction):
        thread_id = interaction.channel.id

        if not await db.is_ai_thread(thread_id):
            await interaction.response.send_message(
                "Эта команда работает только внутри приватного AI-пространства.",
                ephemeral=True,
            )
            return

        await db.reset_thread_history(thread_id)
        await interaction.response.send_message("🔄 Память сброшена. Можно начинать с чистого листа.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIAssistantCog(bot))
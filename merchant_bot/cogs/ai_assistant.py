import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..ai_client import get_ai_response, build_user_content
from ..db import repository as db
from .. import knowledge_base as kb
from .. import storage
from .. import rate_limit
from ..summarizer import maybe_summarize_thread, close_thread_with_summary
from ..response_formatter import format_reply
from ..permissions import has_admin_role

log = logging.getLogger("merchant-bot")


class AIAssistantCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        thread_record = await db.get_thread(thread.id)
        if thread_record is None or not thread_record.active:
            return

        log.info(f"Тред {thread.id} удалён вручную (не через кнопку Close) — закрываем с финальной сводкой")
        try:
            await close_thread_with_summary(thread.id, thread_record.student_id)
        except Exception:
            log.exception(f"Не удалось корректно закрыть удалённый вручную тред {thread.id}")
            await db.deactivate_thread(thread.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        thread_id = message.channel.id

        if not await db.is_ai_thread(thread_id):
            return

        allowed, retry_after = rate_limit.check_and_record(message.author.id)
        if not allowed:
            await message.channel.send(
                f"⏳ Слишком много сообщений подряд — подожди ещё "
                f"{round(retry_after)} сек. и напиши снова.",
                delete_after=10,
            )
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

                summary = await db.get_thread_summary(thread_id)
                if summary:
                    history = [
                        {"role": "system", "content": f"CONVERSATION SUMMARY SO FAR:\n{summary}"}
                    ] + history

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

        await message.channel.send(format_reply(reply))

        try:
            await maybe_summarize_thread(thread_id)
        except Exception:
            log.exception(f"Summarization step failed for thread {thread_id}")

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

    @app_commands.command(name="close", description="Закрыть этот AI-чат (то же самое, что кнопка 🔒 Close this chat)")
    async def close(self, interaction: discord.Interaction):
        thread_id = interaction.channel.id
        thread_record = await db.get_thread(thread_id)

        if thread_record is None or thread_record.kind != "merchant_ai" or not thread_record.active:
            await interaction.response.send_message(
                "Эта команда работает только внутри открытого AI-чата.",
                ephemeral=True,
            )
            return

        if interaction.user.id != thread_record.student_id:
            role_names = {r.name for r in interaction.user.roles}
            if not has_admin_role(role_names):
                await interaction.response.send_message(
                    "Закрыть чат может только тот, кто его открыл, или стафф.", ephemeral=True
                )
                return

        await interaction.response.defer(ephemeral=True)
        await close_thread_with_summary(thread_id, thread_record.student_id)
        await interaction.followup.send(
            "🔒 Чат закрыт и удалён. Можно открыть новый в любой момент.", ephemeral=True
        )

        try:
            await interaction.channel.delete()
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AIAssistantCog(bot))
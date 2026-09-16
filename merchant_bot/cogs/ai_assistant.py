import base64
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

MAX_SCREENSHOTS_PER_MESSAGE = 2


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

        allowed, retry_after, limit_kind = rate_limit.check_and_record(message.author.id)
        if not allowed:
            if limit_kind == "hour":
                wait_text = f"{max(round(retry_after / 60), 1)} мин."
                limit_text = f"не более {rate_limit.MAX_MESSAGES_PER_HOUR} сообщений в час"
            else:
                wait_text = f"{round(retry_after)} сек."
                limit_text = f"не более {rate_limit.MAX_MESSAGES_PER_MINUTE} сообщений в минуту"

            await message.channel.send(
                f"⏳ Слишком много сообщений подряд ({limit_text}) — "
                f"подожди ещё {wait_text} и напиши снова.",
                delete_after=10,
            )
            return

        image_attachments = [
            att for att in message.attachments
            if att.content_type and att.content_type.startswith("image/")
        ]

        if len(image_attachments) > MAX_SCREENSHOTS_PER_MESSAGE:
            skipped = len(image_attachments) - MAX_SCREENSHOTS_PER_MESSAGE
            await message.channel.send(
                f"📎 Обрабатываю только первые {MAX_SCREENSHOTS_PER_MESSAGE} скриншота из "
                f"этого сообщения, остальные {skipped} — пропускаю.",
                delete_after=10,
            )
            image_attachments = image_attachments[:MAX_SCREENSHOTS_PER_MESSAGE]

        image_urls = []
        for att in image_attachments:
            # Модели отдаём картинку как data:-URL (base64), а не ссылку.
            # Discord сам скачивает байты боту напрямую (см. httpx GET выше),
            # а вот доступность presigned-ссылки S3/MinIO для серверов OpenAI
            # не гарантирована (особенно если MinIO поднят на localhost) —
            # data:-URL от этой проблемы не зависит и никогда не протухает.
            try:
                image_bytes = await att.read()
            except discord.HTTPException as e:
                log.error(f"Не удалось скачать вложение из Discord: {e}")
                continue

            b64 = base64.b64encode(image_bytes).decode("ascii")
            image_urls.append(f"data:{att.content_type};base64,{b64}")

            # Отдельно сохраняем оригинал в S3 — только для архива/истории,
            # на отправку модели это уже не влияет, поэтому ошибка тут не критична.
            try:
                await storage.save_screenshot(message.author.id, att.url, att.content_type)
            except Exception as e:
                log.error(f"Screenshot archival upload failed (не блокирует ответ): {e}")

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
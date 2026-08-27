import io
import logging

import discord
from discord.ext import commands

from .. import knowledge_base as kb
from ..ai_client import client as openai_client

log = logging.getLogger("merchant-bot")

KNOWLEDGE_INGESTION_CHANNEL_ID = 1542305456310059038

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md"}
SUPPORTED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

MAX_TITLE_LENGTH = 80


def _make_title(source_label: str, author_name: str, created_at) -> str:
    """
    Формат: [YYYY-MM-DD] Автор — источник
    Пример: [2026-08-27] mika_admin — Скидочная политика для новых партнёров
    Пример (файл): [2026-08-27] mika_admin — objection_handling_v2.pdf
    Пример (фото): [2026-08-27] mika_admin — screenshot.png (image)
    """
    date_str = created_at.strftime("%Y-%m-%d")
    label = source_label.strip().replace("\n", " ")
    if len(label) > MAX_TITLE_LENGTH:
        label = label[:MAX_TITLE_LENGTH - 1].rstrip() + "…"
    return f"[{date_str}] {author_name} — {label}"


async def _extract_text_from_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p for p in pages if p.strip())


async def _extract_text_from_docx(file_bytes: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


async def _describe_image(image_url: str) -> str:
    """
    Прогоняет скриншот/фото через vision-модель и возвращает текстовое
    описание — именно оно и попадёт в базу знаний (эмбеддится как текст).
    """
    response = await openai_client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты помогаешь пополнять базу знаний отдела продаж. Опиши, что изображено "
                    "на скриншоте/фото, максимально подробно и по делу: если это переписка — "
                    "перескажи суть диалога и ключевые реплики; если это документ/таблица/схема — "
                    "перескажи её содержание текстом. Пиши на русском, только содержательное "
                    "описание, без вступлений и оценок."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    )
    return response.choices[0].message.content or ""


class KnowledgeIngestionCog(commands.Cog):
    """
    Слушает канал KNOWLEDGE_INGESTION_CHANNEL_ID. Всё, что туда кидают
    (текст, файлы, изображения), автоматически превращается в запись
    базы знаний — без ручных команд.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != KNOWLEDGE_INGESTION_CHANNEL_ID:
            return
        if message.author.bot:
            return

        added_any = False
        errored_any = False

        text_body = message.content.strip()

        # 1. Простой текст сообщения — сам по себе материал.
        if text_body:
            try:
                title = _make_title(text_body, message.author.display_name, message.created_at)
                await kb.add_entry(title, text_body, added_by=str(message.author))
                added_any = True
            except Exception:
                log.exception("Не удалось добавить текстовое сообщение в базу знаний")
                errored_any = True

        # 2. Вложения — файлы и изображения.
        for attachment in message.attachments:
            try:
                content_type = (attachment.content_type or "").split(";")[0].strip()
                filename_lower = attachment.filename.lower()

                if content_type in SUPPORTED_IMAGE_CONTENT_TYPES:
                    description = await _describe_image(attachment.url)
                    if description.strip():
                        title = _make_title(
                            f"{attachment.filename} (image)", message.author.display_name, message.created_at
                        )
                        await kb.add_entry(title, description, added_by=str(message.author))
                        added_any = True
                    continue

                file_bytes = await attachment.read()

                if filename_lower.endswith(".pdf"):
                    extracted = await _extract_text_from_pdf(file_bytes)
                elif filename_lower.endswith(".docx"):
                    extracted = await _extract_text_from_docx(file_bytes)
                elif any(filename_lower.endswith(ext) for ext in SUPPORTED_TEXT_EXTENSIONS):
                    extracted = file_bytes.decode("utf-8", errors="ignore")
                else:
                    log.warning(f"Неподдерживаемый тип файла в knowledge ingestion: {attachment.filename}")
                    errored_any = True
                    continue

                if extracted.strip():
                    title = _make_title(attachment.filename, message.author.display_name, message.created_at)
                    await kb.add_entry(title, extracted, added_by=str(message.author))
                    added_any = True
                else:
                    log.warning(f"Не удалось извлечь текст из файла: {attachment.filename}")
                    errored_any = True

            except Exception:
                log.exception(f"Не удалось обработать вложение {attachment.filename}")
                errored_any = True

        if added_any:
            try:
                await message.add_reaction("✅")
            except discord.HTTPException:
                pass
        if errored_any:
            try:
                await message.add_reaction("⚠️")
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(KnowledgeIngestionCog(bot))
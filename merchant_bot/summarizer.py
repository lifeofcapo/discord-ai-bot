import json
import logging

from .ai_client import client, MODEL
from .db import repository as db

log = logging.getLogger("merchant-bot")

# Как только в треде накапливается больше этого числа сообщений — сворачиваем
# самую старую часть в summary, чтобы контекст (и счёт за OpenAI) не рос
# бесконтрольно с длиной переписки.
SUMMARIZE_AFTER_MESSAGES = 30

# Сколько самых старых сообщений сворачиваем за один раз. Оставшиеся
# (SUMMARIZE_AFTER_MESSAGES - FOLD_BATCH_SIZE) сообщений остаются "живыми"
# в истории - модель всегда видит свежий кусок диалога дословно.
FOLD_BATCH_SIZE = 20

SUMMARIZER_SYSTEM_PROMPT = """
You're compressing an old portion of the student's (bit seller's) correspondence with Merchant AI. \
in a brief summary for the assistant's memory. Save only what's really important. \
to continue the deal: artist's name/nickname, what beat or product we are talking about, \
discussed prices and offers, agreements, client objections and how \
they answered, the current stage of the deal. Don't repeat the lines verbatim, \
Don't add anything of your own. Write concisely, in Russian, without introductions—straight to the facts.
If there was already a previous summary in the correspondence (helper message "PREVIOUS SUMMARY"), \
Combine it with new facts into one coherent summary without duplicating information.
"""


def _stringify(content) -> str:
    """AIMessage.content может быть строкой или списком (текст+картинки) — приводим к тексту для промпта суммаризатора."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, dict) and block.get("type") == "image_url":
                parts.append("[image attached]")
        return " ".join(parts)
    return str(content)


async def maybe_summarize_thread(thread_id: int):
    total = await db.count_messages(thread_id)
    if total <= SUMMARIZE_AFTER_MESSAGES:
        return

    oldest = await db.get_oldest_messages(thread_id, FOLD_BATCH_SIZE)
    if not oldest:
        return

    existing_summary = await db.get_thread_summary(thread_id)

    transcript_lines = []
    for msg in oldest:
        content = json.loads(msg.content)
        transcript_lines.append(f"{msg.role}: {_stringify(content)}")
    transcript = "\n".join(transcript_lines)

    summarizer_messages = [{"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT}]
    if existing_summary:
        summarizer_messages.append(
            {"role": "user", "content": f"PREVIOUS SUMMARY:\n{existing_summary}"}
        )
    summarizer_messages.append(
        {"role": "user", "content": f"NEW MESSAGES TO FOLD IN:\n{transcript}"}
    )

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=summarizer_messages,
        )
        new_summary = response.choices[0].message.content
    except Exception:
        log.exception(f"Не удалось суммаризировать тред {thread_id} — оставляем историю как есть")
        return

    await db.set_thread_summary(thread_id, new_summary)
    await db.delete_messages([msg.id for msg in oldest])
    log.info(f"Тред {thread_id}: свёрнуто {len(oldest)} старых сообщений в summary")
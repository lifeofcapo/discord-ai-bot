import asyncio
import json
import logging

from .ai_client import client, MODEL
from .db import repository as db

log = logging.getLogger("merchant-bot")

SUMMARIZE_AFTER_MESSAGES = 30
FOLD_BATCH_SIZE = 20

DESCRIBE_IMAGE_MODEL = "gpt-5.4-mini"

DESCRIBE_IMAGE_SYSTEM_PROMPT = """
Briefly and concisely describe the contents of the screenshot showing the conversation \
or document with the beat buyer: key statements, figures, prices, agreements, and objections. \
Write in English, without introductions or subjective commentary—just the essentials.
"""

SUMMARIZER_SYSTEM_PROMPT = """
You're compressing an old portion of the student's (beat seller's) correspondence with Merchant AI. \
in a brief summary for the assistant's memory. Save only what's really important. \
to continue the deal: artist's name/nickname, what beat or product we are talking about, \
discussed prices and offers, agreements, client objections and how \
they answered, the current stage of the deal. Don't repeat the lines verbatim, \
Don't add anything of your own. Write concisely, in Russian, without introductions—straight to the facts.
If there was already a previous summary in the correspondence (helper message "PREVIOUS SUMMARY"), \
Combine it with new facts into one coherent summary without duplicating information.
"""


async def _describe_image(image_url: str) -> str:
    try:
        response = await client.chat.completions.create(
            model=DESCRIBE_IMAGE_MODEL,
            messages=[
                {"role": "system", "content": DESCRIBE_IMAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": image_url}}],
                },
            ],
        )
        description = (response.choices[0].message.content or "").strip()
        return description or "image attached"
    except Exception:
        log.exception("Не удалось описать изображение при суммаризации — использую заглушку")
        return "image attached"


async def _stringify(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)

    image_urls = [
        block["image_url"]["url"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "image_url"
    ]
    descriptions = await asyncio.gather(*(_describe_image(url) for url in image_urls))
    desc_iter = iter(descriptions)

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(block["text"])
        elif block.get("type") == "image_url":
            parts.append(f"[Screenshot: {next(desc_iter)}]")
    return " ".join(parts)


async def _build_transcript(messages) -> str:
    lines = []
    for msg in messages:
        content = json.loads(msg.content)
        stringified = await _stringify(content)
        lines.append(f"{msg.role}: {stringified}")
    return "\n".join(lines)


async def maybe_summarize_thread(thread_id: int):
    total = await db.count_messages(thread_id)
    if total <= SUMMARIZE_AFTER_MESSAGES:
        return

    oldest = await db.get_oldest_messages(thread_id, FOLD_BATCH_SIZE)
    if not oldest:
        return

    existing_summary = await db.get_thread_summary(thread_id)
    transcript = await _build_transcript(oldest)

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


CLOSE_SUMMARY_SYSTEM_PROMPT = """
You are compiling a final summary of the closed thread between the student (beat seller) and Merchant AI for historical and future repeat-buyer context.
Briefly record: who the deal was with (artist/client), what product
was discussed, at what stage the deal was closed (interest/choice/offer/
objection/payment/etc.), the final result (sold/not sold/stuck/unknown), key agreements or reasons for refusal. Write in Russian,
succinctly, factually, without introductions. If a previous summary of the thread has already been created
(PREVIOUS SUMMARY), combine it with new messages into a single final summary.
"""


async def close_thread_with_summary(thread_id: int, student_id: int) -> str:
    remaining = await db.get_all_messages(thread_id)
    existing_summary = await db.get_thread_summary(thread_id)
    total_message_count = await db.count_messages(thread_id)

    if not remaining and not existing_summary:
        final_summary = "Тред закрыт без переписки."
    else:
        transcript = await _build_transcript(remaining) if remaining else (
            "(нет новых сообщений после последней сводки)"
        )

        summarizer_messages = [{"role": "system", "content": CLOSE_SUMMARY_SYSTEM_PROMPT}]
        if existing_summary:
            summarizer_messages.append({"role": "user", "content": f"PREVIOUS SUMMARY:\n{existing_summary}"})
        summarizer_messages.append({"role": "user", "content": f"REMAINING MESSAGES:\n{transcript}"})

        try:
            response = await client.chat.completions.create(model=MODEL, messages=summarizer_messages)
            final_summary = response.choices[0].message.content
        except Exception:
            log.exception(f"Не удалось сгенерировать финальную сводку для треда {thread_id} — сохраняем то, что было")
            final_summary = existing_summary or "Не удалось сгенерировать сводку при закрытии."

    await db.save_closed_thread_summary(thread_id, student_id, final_summary, total_message_count)
    await db.delete_all_messages(thread_id)
    await db.deactivate_thread(thread_id)

    log.info(f"Тред {thread_id} закрыт, raw-история удалена, сводка сохранена")
    return final_summary
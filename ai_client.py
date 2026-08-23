import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from system_prompt import SYSTEM_PROMPT

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


async def get_ai_response(history: list[dict]) -> str:
    """
    history — список сообщений в формате OpenAI, БЕЗ системного промпта
    (он добавляется здесь автоматически на каждый вызов).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    return response.choices[0].message.content


def build_user_content(text: str, image_urls: list[str]) -> list[dict] | str:
    """
    Собирает content сообщения пользователя. Если есть картинки — используем
    мультимодальный формат (список частей), иначе просто текст.
    """
    if not image_urls:
        return text or "(no text, see attached image)"

    content = []
    if text:
        content.append({"type": "text", "text": text})
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content
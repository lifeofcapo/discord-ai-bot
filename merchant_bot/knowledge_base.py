from sqlalchemy import select

from .ai_client import client  
from .db.engine import async_session
from .db.models import KnowledgeBaseEntry

EMBEDDING_MODEL = "text-embedding-3-small"


async def embed_text(text: str) -> list[float]:
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def add_entry(title: str, content: str, added_by: str | None = None) -> KnowledgeBaseEntry:
    embedding = await embed_text(f"{title}\n\n{content}")
    async with async_session() as session:
        entry = KnowledgeBaseEntry(title=title, content=content, embedding=embedding, added_by=added_by)
        session.add(entry)
        await session.commit()
        return entry


async def deactivate_entry(entry_id: int) -> bool:
    #Не удаляем — помечаем неактивным, версионирование.
    async with async_session() as session:
        entry = await session.get(KnowledgeBaseEntry, entry_id)
        if entry is None:
            return False
        entry.active = False
        await session.commit()
        return True


async def search(query: str, top_k: int = 4) -> list[KnowledgeBaseEntry]:
    query_embedding = await embed_text(query)

    async with async_session() as session:
        result = await session.execute(
            select(KnowledgeBaseEntry)
            .where(KnowledgeBaseEntry.active == True)  # noqa: E712
            .order_by(KnowledgeBaseEntry.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        return list(result.scalars().all())


def format_for_prompt(entries: list[KnowledgeBaseEntry]) -> str:
    if not entries:
        return ""
    blocks = [f"### {e.title}\n{e.content}" for e in entries]
    return "RELEVANT KNOWLEDGE BASE ENTRIES:\n\n" + "\n\n".join(blocks)
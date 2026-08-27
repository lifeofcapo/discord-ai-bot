import json

from sqlalchemy import select, update, func

from .engine import async_session
from .models import Student, AIThread, AIMessage


async def get_or_create_student(user_id: int, display_name: str) -> Student:
    async with async_session() as session:
        student = await session.get(Student, user_id)
        if student is None:
            student = Student(id=user_id, display_name=display_name)
            session.add(student)
            await session.commit()
        return student


async def get_active_thread(student_id: int, kind: str) -> AIThread | None:
    async with async_session() as session:
        result = await session.execute(
            select(AIThread).where(
                AIThread.student_id == student_id,
                AIThread.kind == kind,
                AIThread.active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()


async def create_thread(thread_id: int, student_id: int, kind: str) -> AIThread:
    async with async_session() as session:
        thread = AIThread(id=thread_id, student_id=student_id, kind=kind)
        session.add(thread)
        await session.commit()
        return thread


async def deactivate_thread(thread_id: int):
    async with async_session() as session:
        await session.execute(
            update(AIThread).where(AIThread.id == thread_id).values(active=False)
        )
        await session.commit()


async def is_ai_thread(thread_id: int) -> bool:
    async with async_session() as session:
        thread = await session.get(AIThread, thread_id)
        return thread is not None and thread.kind == "merchant_ai" and thread.active


async def append_message(thread_id: int, role: str, content):
    async with async_session() as session:
        session.add(AIMessage(thread_id=thread_id, role=role, content=json.dumps(content)))
        await session.commit()


async def get_history(thread_id: int, limit: int = 40) -> list[dict]:
    async with async_session() as session:
        result = await session.execute(
            select(AIMessage)
            .where(AIMessage.thread_id == thread_id)
            .order_by(AIMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": json.loads(m.content)} for m in messages]


async def count_messages(thread_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(AIMessage).where(AIMessage.thread_id == thread_id)
        )
        return result.scalar_one()


async def get_thread_summary(thread_id: int) -> str | None:
    async with async_session() as session:
        thread = await session.get(AIThread, thread_id)
        return thread.summary if thread else None


async def set_thread_summary(thread_id: int, summary: str):
    async with async_session() as session:
        await session.execute(
            update(AIThread).where(AIThread.id == thread_id).values(summary=summary)
        )
        await session.commit()


async def get_oldest_messages(thread_id: int, count: int) -> list[AIMessage]:
    async with async_session() as session:
        result = await session.execute(
            select(AIMessage)
            .where(AIMessage.thread_id == thread_id)
            .order_by(AIMessage.created_at.asc())
            .limit(count)
        )
        return list(result.scalars().all())


async def delete_messages(message_ids: list[int]):
    async with async_session() as session:
        result = await session.execute(select(AIMessage).where(AIMessage.id.in_(message_ids)))
        for msg in result.scalars().all():
            await session.delete(msg)
        await session.commit()


async def reset_thread_history(thread_id: int):
    async with async_session() as session:
        result = await session.execute(select(AIMessage).where(AIMessage.thread_id == thread_id))
        for msg in result.scalars().all():
            await session.delete(msg)
        await session.execute(
            update(AIThread).where(AIThread.id == thread_id).values(summary=None)
        )
        await session.commit()
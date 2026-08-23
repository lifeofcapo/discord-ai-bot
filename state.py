#temporary storage, then replace to Postgres
# thread_id -> список сообщений в формате OpenAI [{"role": ..., "content": ...}, ...]
ai_thread_history: dict[int, list[dict]] = {}


def register_ai_thread(thread_id: int):
    ai_thread_history[thread_id] = []


def is_ai_thread(thread_id: int) -> bool:
    return thread_id in ai_thread_history


def get_history(thread_id: int) -> list[dict]:
    return ai_thread_history.get(thread_id, [])


def append_message(thread_id: int, role: str, content):
    if thread_id not in ai_thread_history:
        ai_thread_history[thread_id] = []
    ai_thread_history[thread_id].append({"role": role, "content": content})


def reset_thread(thread_id: int):
    ai_thread_history[thread_id] = []
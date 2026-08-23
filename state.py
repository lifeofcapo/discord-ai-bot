
#temporary storage, then need to be replaced with Postgres.
import time

# thread_id -> список сообщений в формате OpenAI [{"role": ..., "content": ...}, ...]
ai_thread_history: dict[int, list[dict]] = {}

# (user_id, kind) -> thread_id — to avoid doubles
# kind: "merchant_ai" | "support"
active_threads: dict[tuple[int, str], int] = {}

# (user_id, kind) -> defence from double-click
_last_click: dict[tuple[int, str], float] = {}
COOLDOWN_SECONDS = 4


def is_on_cooldown(user_id: int, kind: str) -> bool:
    key = (user_id, kind)
    last = _last_click.get(key)
    now = time.monotonic()
    if last is not None and (now - last) < COOLDOWN_SECONDS:
        return True
    _last_click[key] = now
    return False


def get_active_thread_id(user_id: int, kind: str) -> int | None:
    return active_threads.get((user_id, kind))


def set_active_thread_id(user_id: int, kind: str, thread_id: int):
    active_threads[(user_id, kind)] = thread_id


def clear_active_thread_id(user_id: int, kind: str):
    active_threads.pop((user_id, kind), None)


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
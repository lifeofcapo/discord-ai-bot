"""
Осталась только защита от двойного клика — она не критична для персистентности,
поэтому остаётся в оперативной памяти. Вся остальная память (история диалогов,
активные треды) теперь в PostgreSQL — см. db/repository.py.
"""
import time

# (user_id, kind) -> timestamp последнего клика
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
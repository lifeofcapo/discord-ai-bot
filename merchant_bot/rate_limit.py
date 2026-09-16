import time
from collections import defaultdict, deque

MAX_MESSAGES_PER_MINUTE = 3
MINUTE_WINDOW_SECONDS = 60

MAX_MESSAGES_PER_HOUR = 60
HOUR_WINDOW_SECONDS = 3600

_minute_timestamps: dict[int, deque[float]] = defaultdict(deque)
_hour_timestamps: dict[int, deque[float]] = defaultdict(deque)


def _trim(timestamps: deque[float], now: float, window: float) -> None:
    while timestamps and now - timestamps[0] > window:
        timestamps.popleft()


def check_and_record(user_id: int) -> tuple[bool, float, str | None]:
    """Проверяет оба окна (минута и час) для пользователя.

    Возвращает (allowed, retry_after_seconds, limit_kind).
    limit_kind — "minute" или "hour", какой именно лимит сработал (None, если allowed=True).
    Если сообщение не проходит ни одну из проверок, оно не засчитывается
    ни в один из счётчиков — пользователь не "теряет" попытку впустую.
    """
    now = time.monotonic()

    minute_ts = _minute_timestamps[user_id]
    hour_ts = _hour_timestamps[user_id]

    _trim(minute_ts, now, MINUTE_WINDOW_SECONDS)
    _trim(hour_ts, now, HOUR_WINDOW_SECONDS)

    if len(minute_ts) >= MAX_MESSAGES_PER_MINUTE:
        retry_after = MINUTE_WINDOW_SECONDS - (now - minute_ts[0])
        return False, max(retry_after, 0), "minute"

    if len(hour_ts) >= MAX_MESSAGES_PER_HOUR:
        retry_after = HOUR_WINDOW_SECONDS - (now - hour_ts[0])
        return False, max(retry_after, 0), "hour"

    minute_ts.append(now)
    hour_ts.append(now)
    return True, 0.0, None
import time
from collections import defaultdict, deque

MAX_MESSAGES = 3
WINDOW_SECONDS = 60

# user_id -> deque timestamps последних сообщений (в пределах окна)
_message_timestamps: dict[int, deque[float]] = defaultdict(deque)


def check_and_record(user_id: int) -> tuple[bool, float]:
    now = time.monotonic()
    timestamps = _message_timestamps[user_id]

    # выбрасываем записи старше окна
    while timestamps and now - timestamps[0] > WINDOW_SECONDS:
        timestamps.popleft()

    if len(timestamps) >= MAX_MESSAGES:
        retry_after = WINDOW_SECONDS - (now - timestamps[0])
        return False, max(retry_after, 0)

    timestamps.append(now)
    return True, 0.0
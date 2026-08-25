import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")

import pytest

from merchant_bot import state as state_module


@pytest.fixture(autouse=True)
def reset_state():
#обнулить in memory, чтобы не мешать тесту
    state_module.ai_thread_history.clear()
    state_module.active_threads.clear()
    state_module._last_click.clear()
    yield
    state_module.ai_thread_history.clear()
    state_module.active_threads.clear()
    state_module._last_click.clear()
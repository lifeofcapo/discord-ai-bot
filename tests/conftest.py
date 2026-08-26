import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")

import pytest

from merchant_bot import state as state_module


@pytest.fixture(autouse=True)
def reset_cooldowns():
    state_module._last_click.clear()
    yield
    state_module._last_click.clear()
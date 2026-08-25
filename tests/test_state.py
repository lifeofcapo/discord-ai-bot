from merchant_bot import state


class TestCooldown:
    def test_first_click_is_not_on_cooldown(self):
        assert state.is_on_cooldown(user_id=1, kind="merchant_ai") is False

    def test_immediate_second_click_is_blocked(self):
        state.is_on_cooldown(user_id=1, kind="merchant_ai")  # первый клик
        assert state.is_on_cooldown(user_id=1, kind="merchant_ai") is True

    def test_different_users_do_not_share_cooldown(self):
        assert state.is_on_cooldown(user_id=1, kind="merchant_ai") is False
        assert state.is_on_cooldown(user_id=2, kind="merchant_ai") is False

    def test_different_kinds_do_not_share_cooldown(self):
        assert state.is_on_cooldown(user_id=1, kind="merchant_ai") is False
        assert state.is_on_cooldown(user_id=1, kind="support") is False


class TestActiveThreadTracking:
    def test_no_active_thread_by_default(self):
        assert state.get_active_thread_id(user_id=1, kind="merchant_ai") is None

    def test_set_and_get_active_thread(self):
        state.set_active_thread_id(user_id=1, kind="merchant_ai", thread_id=999)
        assert state.get_active_thread_id(user_id=1, kind="merchant_ai") == 999

    def test_clear_active_thread(self):
        state.set_active_thread_id(user_id=1, kind="merchant_ai", thread_id=999)
        state.clear_active_thread_id(user_id=1, kind="merchant_ai")
        assert state.get_active_thread_id(user_id=1, kind="merchant_ai") is None

    def test_merchant_ai_and_support_are_independent(self):
        state.set_active_thread_id(user_id=1, kind="merchant_ai", thread_id=111)
        state.set_active_thread_id(user_id=1, kind="support", thread_id=222)
        assert state.get_active_thread_id(user_id=1, kind="merchant_ai") == 111
        assert state.get_active_thread_id(user_id=1, kind="support") == 222


class TestAIThreadHistory:
    def test_thread_is_not_ai_thread_until_registered(self):
        assert state.is_ai_thread(123) is False

    def test_register_marks_thread_as_ai_thread(self):
        state.register_ai_thread(123)
        assert state.is_ai_thread(123) is True

    def test_append_and_get_history(self):
        state.register_ai_thread(123)
        state.append_message(123, "user", "hello")
        state.append_message(123, "assistant", "hi there")
        assert state.get_history(123) == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]

    def test_reset_clears_history_but_keeps_thread_registered(self):
        state.register_ai_thread(123)
        state.append_message(123, "user", "hello")
        state.reset_thread(123)
        assert state.get_history(123) == []
        assert state.is_ai_thread(123) is True
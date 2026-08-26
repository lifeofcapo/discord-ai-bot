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
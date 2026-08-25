from merchant_bot.permissions import has_admin_role


class TestHasAdminRole:
    def test_the_standard_is_authorized(self):
        assert has_admin_role({"THE STANDARD"}) is True

    def test_technical_administrator_is_authorized(self):
        assert has_admin_role({"TECHNICAL ADMIN"}) is True

    def test_plain_merchant_is_not_authorized(self):
        assert has_admin_role({"MERCHANT", "OWNED CATALOG"}) is False

    def test_no_roles_is_not_authorized(self):
        assert has_admin_role(set()) is False

    def test_unrelated_roles_are_not_authorized(self):
        assert has_admin_role({"PARTNER CATALOG", "OWNED CATALOG"}) is False
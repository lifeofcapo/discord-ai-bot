from merchant_bot.ai_client import build_user_content


class TestBuildUserContent:
    def test_text_only_returns_plain_string(self):
        result = build_user_content("hello there", [])
        assert result == "hello there"

    def test_empty_text_no_images_has_fallback_text(self):
        result = build_user_content("", [])
        assert result == "(no text, see attached image)"

    def test_single_image_produces_multimodal_list(self):
        result = build_user_content("check this", ["https://example.com/a.png"])
        assert isinstance(result, list)
        assert {"type": "text", "text": "check this"} in result
        assert any(part["type"] == "image_url" for part in result)

    def test_image_url_is_passed_through_correctly(self):
        result = build_user_content("", ["https://example.com/a.png"])
        image_parts = [p for p in result if p["type"] == "image_url"]
        assert image_parts[0]["image_url"]["url"] == "https://example.com/a.png"

    def test_no_text_part_when_text_is_empty(self):
        result = build_user_content("", ["https://example.com/a.png"])
        assert all(part["type"] != "text" for part in result)

    def test_multiple_images_all_included(self):
        urls = ["https://example.com/a.png", "https://example.com/b.png"]
        result = build_user_content("compare these", urls)
        image_urls = [p["image_url"]["url"] for p in result if p["type"] == "image_url"]
        assert image_urls == urls
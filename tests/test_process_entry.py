import unittest
from unittest.mock import patch

from main import Config, process_entry


class MinifluxClient:
    def __init__(self):
        self.updated_entry_id = None
        self.updated_fields = None

    def update_entry(self, entry_id, **fields):
        self.updated_entry_id = entry_id
        self.updated_fields = fields


class ProcessEntryTestCase(unittest.TestCase):
    def test_translate_content_and_title(self):
        config = Config.__new__(Config)
        config.llm_max_length = None
        config.title_translate_prompt = "title prompt"
        config.content_translate_prompt = "content prompt"
        client = MinifluxClient()
        entry = {
            "id": 1,
            "title": "Original title",
            "content": "<p>Original content</p>",
        }

        def fake_translate(config, prompt, content):
            if prompt == "title prompt":
                return "翻译标题"
            return "<p>翻译内容</p>"

        with patch("main.translate_text", side_effect=fake_translate):
            process_entry(config, client, entry)

        self.assertEqual(client.updated_entry_id, 1)
        self.assertEqual(
            client.updated_fields["title"],
            "翻译标题 || Original title",
        )
        self.assertEqual(
            client.updated_fields["content"],
            "<p>翻译内容</p><br /><hr><br /><p>Original content</p>",
        )


if __name__ == "__main__":
    unittest.main()

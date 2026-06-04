import os
import unittest

from main import Config


_ENV_KEYS = [
    "MINIFLUX_BASE_URL", "MINIFLUX_API_KEY",
    "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
    "LLM_MAX_LENGTH", "LLM_TIMEOUT",
    "TITLE_TRANSLATE_PROMPT", "CONTENT_TRANSLATE_PROMPT",
]


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in _ENV_KEYS}
        for k in ("MINIFLUX_BASE_URL", "MINIFLUX_API_KEY",
                  "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
            os.environ.setdefault(k, "test")

    def tearDown(self):
        for k in _ENV_KEYS:
            val = self._saved.get(k)
            if val is not None:
                os.environ[k] = val
            else:
                os.environ.pop(k, None)

    def test_title_translate_prompt_default(self):
        config = Config()
        self.assertIn("Translate only the text", config.title_translate_prompt)

    def test_content_translate_prompt_default(self):
        config = Config()
        self.assertIn("HTML content translation", config.content_translate_prompt)

    def test_llm_max_length_default(self):
        config = Config()
        self.assertEqual(config.llm_max_length, 8192)

    def test_title_translate_prompt_override(self):
        os.environ["TITLE_TRANSLATE_PROMPT"] = "custom title prompt"
        config = Config()
        self.assertEqual(config.title_translate_prompt, "custom title prompt")

    def test_content_translate_prompt_override(self):
        os.environ["CONTENT_TRANSLATE_PROMPT"] = "custom content prompt"
        config = Config()
        self.assertEqual(config.content_translate_prompt, "custom content prompt")

    def test_missing_required_env_raises(self):
        os.environ.pop("LLM_MODEL")
        with self.assertRaisesRegex(ValueError, "LLM_MODEL is required"):
            Config()

    def test_optional_number_config(self):
        os.environ["LLM_MAX_LENGTH"] = "100"
        os.environ["LLM_TIMEOUT"] = "5"
        config = Config()
        self.assertEqual(config.llm_max_length, 100)
        self.assertEqual(config.llm_timeout, 5)


if __name__ == "__main__":
    unittest.main()

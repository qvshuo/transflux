import json
import logging
import os
import re
import time
import urllib.request


DEFAULT_TITLE_TRANSLATE_PROMPT = (
    "You are a professional, authentic translation engine. "
    "Translate only the text into Simplified Chinese, "
    "return exactly one final translation and nothing else. "
    "Do not include explanations, notes, alternatives, markdown, apologies, "
    "or self-corrections."
)


DEFAULT_CONTENT_TRANSLATE_PROMPT = """You are a professional, authentic translation engine specialized in HTML content translation.

Requirements:
1. Translate only the text content into Simplified Chinese
2. Preserve ALL HTML tags, attributes, and structure completely unchanged
3. Maintain proper context awareness across different HTML elements and their relationships
4. Consider semantic meaning within nested tags and their hierarchical context
5. Ensure translated text fits naturally within the HTML structure
6. Keep inline elements (like <span>, <a>, <strong>) contextually coherent with their surrounding text
7. Maintain consistency in terminology throughout the entire HTML document
8. Return only the translated HTML content without explanations or comments

Important: Do not modify, remove, or alter any HTML tags, attributes, classes, IDs, or structural elements. Only translate the actual text content between tags."""


class Config:
    def __init__(self):
        env = os.getenv

        def required(key):
            value = env(key)
            if not value:
                raise ValueError(f"{key} is required")
            return value

        self.miniflux_base_url = required("MINIFLUX_BASE_URL")
        self.miniflux_api_key = required("MINIFLUX_API_KEY")
        self.llm_base_url = required("LLM_BASE_URL")
        self.llm_api_key = required("LLM_API_KEY")
        self.llm_model = required("LLM_MODEL")
        self.llm_max_length = int(env("LLM_MAX_LENGTH", "8192"))
        self.llm_timeout = int(env("LLM_TIMEOUT", "60"))
        self.title_translate_prompt = env(
            "TITLE_TRANSLATE_PROMPT",
            DEFAULT_TITLE_TRANSLATE_PROMPT,
        )
        self.content_translate_prompt = env(
            "CONTENT_TRANSLATE_PROMPT",
            DEFAULT_CONTENT_TRANSLATE_PROMPT,
        )


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
TITLE_TRANSLATION_SEPARATOR = " || "
CONTENT_TRANSLATION_SEPARATOR = "<br /><hr><br />"


def translate_text(config, prompt, text):
    if config.llm_max_length and len(text) > config.llm_max_length:
        text = text[: config.llm_max_length]

    if "${title}" in prompt:
        user_content = prompt.replace("${title}", text)
    elif "${content}" in prompt:
        user_content = prompt.replace("${content}", text)
    else:
        user_content = None

    if user_content:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_content},
        ]
    else:
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "The following is the input content:\n---\n" + text,
            },
        ]

    payload = json.dumps({"model": config.llm_model, "messages": messages}).encode()
    http_request = urllib.request.Request(
        url=config.llm_base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config.llm_api_key,
        },
    )
    http_response = urllib.request.urlopen(http_request, timeout=config.llm_timeout)
    return json.loads(http_response.read())["choices"][0]["message"]["content"]


def is_chinese_content(text, threshold=0.05):
    if not text:
        return False
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return cjk_chars / max(len(text), 1) > threshold


def process_entry(config, miniflux_client, entry):
    entry_id = entry["id"]
    original_title = entry["title"]
    original_content = entry["content"]
    update_fields = {}

    try:
        if is_chinese_content(original_title):
            logger.info(f"skip zh title entry id:{entry_id}")
        else:
            translated_title = translate_text(
                config,
                config.title_translate_prompt,
                original_title,
            )
            update_fields["title"] = (
                translated_title + TITLE_TRANSLATION_SEPARATOR + original_title
            )

        if is_chinese_content(original_content):
            logger.info(f"skip zh content entry id:{entry_id}")
        else:
            translated_content = translate_text(
                config,
                config.content_translate_prompt,
                original_content,
            )
            update_fields["content"] = (
                translated_content + CONTENT_TRANSLATION_SEPARATOR + original_content
            )

        if not update_fields:
            logger.info(f"skip zh entry id:{entry_id}")
            return

        miniflux_client.update_entry(entry_id, **update_fields)
    except Exception as e:
        logger.error(f"Error processing entry {entry_id}: {e}")
        return

    log_preview = (update_fields.get("title") or update_fields.get("content") or "")[
        :20
    ] + "..."
    logger.info(f"entry_id:{entry_id} result:{log_preview}")


def process_unread_entries(config, miniflux_client):
    entries_response = miniflux_client.get_entries(status=["unread"], limit=1000)
    unread_entries = entries_response["entries"]
    if unread_entries:
        logger.info(f"Get unread entries: {len(unread_entries)}")
    else:
        logger.info("No new entries")
        return

    for entry in unread_entries:
        process_entry(config, miniflux_client, entry)


def main():
    import miniflux

    config = Config()
    miniflux_client = miniflux.Client(
        config.miniflux_base_url, api_key=config.miniflux_api_key
    )
    while True:
        try:
            miniflux_client.me()
            logger.info("Successfully connected to Miniflux!")
            break
        except Exception as e:
            logger.error(f"Cannot connect to Miniflux: {e}")
            time.sleep(3)

    while True:
        try:
            process_unread_entries(config, miniflux_client)
        except Exception as e:
            logger.error(f"Process unread entries failed: {e}")
        time.sleep(60)


if __name__ == "__main__":
    main()

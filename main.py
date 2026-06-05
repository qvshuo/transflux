import logging
import os
import re
import time
from typing import Any

import httpx
import miniflux


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
TITLE_TRANSLATION_SEPARATOR = " ||| "
CONTENT_TRANSLATION_SEPARATOR = '<br /><hr data-transflux="translated">'


def already_translated(entry: dict[str, Any]) -> bool:
    title = entry.get("title") or ""
    content = entry.get("content") or ""
    return (
        TITLE_TRANSLATION_SEPARATOR in title
        or CONTENT_TRANSLATION_SEPARATOR in content
    )


def build_messages(prompt: str, text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]


def call_llm(config: "Config", messages: list[dict[str, str]]) -> str:
    url = config.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + config.llm_api_key,
    }
    payload = {"model": config.llm_model, "messages": messages}

    delay = 2
    last_error = None
    for attempt in range(3):
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=config.llm_timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            last_error = e
            if attempt < 2:
                logger.warning("LLM request failed, retrying in %s seconds: %s", delay, e)
                time.sleep(delay)
                delay *= 2

    raise RuntimeError(f"LLM request failed after retries: {last_error}")


def translate_text(config: "Config", prompt: str, text: str) -> str:
    return call_llm(config, build_messages(prompt, text))


def is_chinese_content(text: str, threshold: float = 0.05) -> bool:
    if not text:
        return False

    plain = re.sub(r"<[^>]+>", "", text)
    plain = re.sub(r"https?://\S+", "", plain)
    plain = re.sub(r"\s+", "", plain)
    if not plain:
        return False

    cjk_chars = sum(1 for char in plain if "\u4e00" <= char <= "\u9fff")
    return cjk_chars / len(plain) > threshold


def process_entry(config: "Config", miniflux_client: Any, entry: dict[str, Any]) -> None:
    entry_id = entry["id"]
    original_title = entry.get("title") or ""
    original_content = entry.get("content") or ""

    if already_translated(entry):
        logger.info("skip translated entry id:%s", entry_id)
        return

    new_title = None
    new_content = None

    try:
        if not original_title:
            logger.info("skip empty title entry id:%s", entry_id)
        elif is_chinese_content(original_title):
            logger.info("skip zh title entry id:%s", entry_id)
        elif config.llm_max_length and len(original_title) > config.llm_max_length:
            logger.warning(
                "skip long title translation entry id:%s length:%s max:%s",
                entry_id,
                len(original_title),
                config.llm_max_length,
            )
        else:
            translated_title = translate_text(
                config,
                config.title_translate_prompt,
                original_title,
            )
            new_title = translated_title + TITLE_TRANSLATION_SEPARATOR + original_title

        if not original_content:
            logger.info("skip empty content entry id:%s", entry_id)
        elif is_chinese_content(original_content):
            logger.info("skip zh content entry id:%s", entry_id)
        elif config.llm_max_length and len(original_content) > config.llm_max_length:
            logger.warning(
                "skip long content translation entry id:%s length:%s max:%s",
                entry_id,
                len(original_content),
                config.llm_max_length,
            )
        else:
            translated_content = translate_text(
                config,
                config.content_translate_prompt,
                original_content,
            )
            new_content = translated_content + CONTENT_TRANSLATION_SEPARATOR + original_content

        update_fields = {}
        if new_title is not None:
            update_fields["title"] = new_title
        if new_content is not None:
            update_fields["content"] = new_content

        if not update_fields:
            logger.info("skip entry id:%s no update needed", entry_id)
            return

        miniflux_client.update_entry(entry_id, **update_fields)
    except Exception as e:
        logger.error("Error processing entry %s: %s", entry_id, e)
        return

    preview_source = update_fields.get("title") or update_fields.get("content") or ""
    log_preview = preview_source[:20] + ("..." if len(preview_source) > 20 else "")
    logger.info("entry_id:%s result:%s", entry_id, log_preview)


def process_unread_entries(config: "Config", miniflux_client: Any) -> None:
    entries_response = miniflux_client.get_entries(status=["unread"], limit=1000)
    unread_entries = entries_response["entries"]
    if unread_entries:
        logger.info("Get unread entries: %s", len(unread_entries))
    else:
        logger.info("No new entries")
        return

    for entry in unread_entries:
        process_entry(config, miniflux_client, entry)


def wait_for_miniflux(miniflux_client: Any) -> None:
    delay = 3
    while True:
        try:
            miniflux_client.me()
            logger.info("Successfully connected to Miniflux!")
            return
        except Exception as e:
            logger.error("Cannot connect to Miniflux: %s", e)
            logger.info("Retrying in %s seconds", delay)
            time.sleep(delay)
            delay = min(delay * 2, 300)


def main() -> None:
    config = Config()
    miniflux_client = miniflux.Client(
        config.miniflux_base_url, api_key=config.miniflux_api_key
    )

    wait_for_miniflux(miniflux_client)

    while True:
        try:
            process_unread_entries(config, miniflux_client)
        except Exception as e:
            logger.error("Process unread entries failed: %s", e)
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully")

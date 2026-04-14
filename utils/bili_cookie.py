from __future__ import annotations

import json
from pathlib import Path

COOKIE_DIR_NAME = "cook"
COOKIE_FILE_NAME = "bili_cookies.json"
SUPPORTED_COOKIE_FILES = (
    "bili_cookies.json",
    "bili_cookie.json",
    "cookies.json",
    "cookie.json",
    "bili_cookies.txt",
    "bili_cookie.txt",
    "cookies.txt",
    "cookie.txt",
)


def get_cookie_dir() -> Path:
    return Path(__file__).resolve().parent.parent / COOKIE_DIR_NAME


def get_cookie_file() -> Path:
    return get_cookie_dir() / COOKIE_FILE_NAME


def build_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items() if key and value)


def parse_cookie_string(cookie_text: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for item in (cookie_text or "").split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            cookies[key] = value
    return cookies


def normalize_cookie_payload(payload) -> dict[str, str]:
    if isinstance(payload, dict):
        return {
            str(key).strip(): str(value).strip()
            for key, value in payload.items()
            if str(key).strip() and str(value).strip()
        }

    if isinstance(payload, list):
        cookies: dict[str, str] = {}
        for item in payload:
            if isinstance(item, dict) and "name" in item and "value" in item:
                key = str(item["name"]).strip()
                value = str(item["value"]).strip()
                if key and value:
                    cookies[key] = value
        return cookies

    if isinstance(payload, str):
        return parse_cookie_string(payload)

    return {}


def find_cookie_file() -> Path | None:
    cookie_dir = get_cookie_dir()
    if not cookie_dir.exists():
        return None

    for file_name in SUPPORTED_COOKIE_FILES:
        candidate = cookie_dir / file_name
        if candidate.exists() and candidate.is_file():
            return candidate

    for candidate in sorted(cookie_dir.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() in {".json", ".txt"}:
            return candidate

    return None


def load_bili_cookies() -> dict[str, str]:
    cookie_file = find_cookie_file()
    if cookie_file is None:
        return {}

    raw_text = cookie_file.read_text(encoding="utf-8").strip()
    if not raw_text:
        return {}

    if cookie_file.suffix.lower() == ".json":
        try:
            return normalize_cookie_payload(json.loads(raw_text))
        except json.JSONDecodeError:
            return parse_cookie_string(raw_text)

    return parse_cookie_string(raw_text)


def save_bili_cookies(cookies: dict[str, str]) -> Path:
    cookie_dir = get_cookie_dir()
    cookie_dir.mkdir(parents=True, exist_ok=True)
    cookie_file = get_cookie_file()
    cookie_file.write_text(
        json.dumps(normalize_cookie_payload(cookies), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cookie_file

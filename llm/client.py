from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config import (
    NVIDIA_API_ENDPOINT,
    NVIDIA_API_KEY_ENV,
    NVIDIA_TEXT_MODEL,
    NVIDIA_VISION_MODEL,
    VISION_KEYWORDS,
)
from logger import app_logger

MAX_LOG_CHARS = 1200


class VisionKeywordRouter:
    def __init__(self, keywords: list[str] | None = None) -> None:
        self.keywords = [keyword.lower() for keyword in (keywords or VISION_KEYWORDS)]

    def is_visual_query(self, query: str) -> bool:
        lowered = query.lower()
        return any(keyword in lowered for keyword in self.keywords)



def call_text_model(prompt: str) -> str:
    api_key = _get_secret(NVIDIA_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(_missing_key_message("NVIDIA API key", NVIDIA_API_KEY_ENV))

    payload = {
        "model": NVIDIA_TEXT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are PraSush, a fast bilingual ambient AI assistant. "
                    "Reply in the same language as the current user turn. "
                    "Do not drift into another language unless the user explicitly asks."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 320,
    }

    app_logger.info(f"[MODEL USED] NVIDIA ({NVIDIA_TEXT_MODEL})")
    app_logger.llm_request(prompt)
    data = _execute_openai_compatible_chat_completion(api_key=api_key, payload=payload, request_label="NVIDIA")
    parsed = _parse_response(data)
    _log_model_result(data, parsed)
    return parsed



def call_vision_model(image_path: str, prompt: str) -> str:
    api_key = _get_secret(NVIDIA_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(_missing_key_message("NVIDIA API key", NVIDIA_API_KEY_ENV))

    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are PraSush, a bilingual visual assistant. "
                    "Answer visual questions in the same language as the current user turn."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_encode_image(image_path)}"}},
                ],
            },
        ],
        "temperature": 0.4,
        "max_tokens": 320,
    }

    app_logger.info(f"[MODEL USED] NVIDIA Vision ({NVIDIA_VISION_MODEL})")
    app_logger.info(f"Vision image path: {image_path}")
    app_logger.llm_request(prompt)
    data = _execute_openai_compatible_chat_completion(api_key=api_key, payload=payload, request_label="NVIDIA vision")
    parsed = _parse_response(data)
    _log_model_result(data, parsed)
    return parsed



def _execute_openai_compatible_chat_completion(api_key: str, payload: dict[str, Any], request_label: str) -> dict[str, Any]:
    if OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key, base_url=NVIDIA_API_ENDPOINT)
            response = client.chat.completions.create(**payload)
            return response.model_dump()
        except Exception as exc:
            app_logger.warning(f"{request_label} SDK request failed: {exc}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response: requests.Response | None = None
    try:
        response = requests.post(f"{NVIDIA_API_ENDPOINT}/chat/completions", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        raise RuntimeError(_format_http_error(response, payload.get("model"))) from exc
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"{request_label} request failed: {exc}") from exc



def _parse_response(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("NVIDIA response did not include choices.")
    first = choices[0]
    if isinstance(first, dict):
        message = first.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or content is None:
            content = first.get("content")
        parsed = content.strip() if isinstance(content, str) else ""
        if not parsed:
            reasoning = message.get("reasoning_content") or first.get("reasoning_content")
            if isinstance(reasoning, str) and reasoning.strip():
                parsed = reasoning.strip()
            else:
                raise RuntimeError("NVIDIA response did not include assistant content.")
        return parsed
    raise RuntimeError("Unexpected NVIDIA response format for choices.")



def _format_http_error(response: requests.Response | None, model_name: Any) -> str:
    status_code = response.status_code if response is not None else "unknown"
    reason = response.reason if response is not None else "Unknown"
    body_preview = response.text[:300] if response is not None and response.text else ""
    return (
        f"NVIDIA request failed: {status_code} {reason}. "
        f"Check {NVIDIA_API_KEY_ENV}, verify access to model '{model_name}', and confirm the endpoint is enabled. "
        f"Response body: {body_preview}"
    )



def _log_model_result(data: dict[str, Any], parsed: str) -> None:
    raw_preview = json.dumps(data, ensure_ascii=False)
    app_logger.debug(f"[RAW RESPONSE] {_truncate(raw_preview)}")
    app_logger.debug(f"[PARSED RESPONSE] {parsed}")
    app_logger.llm_response(parsed)



def _truncate(value: str, max_chars: int = MAX_LOG_CHARS) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."



def _missing_key_message(label: str, env_name: str) -> str:
    return f"Missing {label}. Set '{env_name}' in the current shell or in a local .env file."



def _get_secret(env_name: str) -> str:
    value = os.getenv(env_name, "").strip()
    if value:
        return value

    for filename in (".env", ".env.local"):
        path = Path(filename)
        if not path.exists():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, file_value = line.split("=", 1)
                if key.strip() == env_name:
                    return file_value.strip().strip("'").strip('"')
        except OSError as exc:
            app_logger.warning(f"Failed to read {filename}: {exc}")
    return ""



def _encode_image(image_path: str) -> str:
    image_bytes = Path(image_path).read_bytes()
    return base64.b64encode(image_bytes).decode("utf-8")




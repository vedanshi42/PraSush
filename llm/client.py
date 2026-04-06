from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests

from config import (
    AUTO_UNLOAD_VISION,
    COMET_API_ENDPOINT,
    COMET_API_KEY_ENV,
    COMET_MODEL,
    GOOGLE_API_ENDPOINT,
    GOOGLE_API_KEY_ENV,
    GOOGLE_MODEL,
    LLM_PROVIDER,
    OLLAMA_ENDPOINT,
    OLLAMA_TEXT_MODEL,
    USE_VISION,
    VISION_KEYWORDS,
    VISION_MODEL,
)
from logger import app_logger


class VisionKeywordRouter:
    def __init__(self, keywords: list[str] | None = None) -> None:
        self.keywords = [keyword.lower() for keyword in (keywords or VISION_KEYWORDS)]

    def is_visual_query(self, query: str) -> bool:
        lowered = query.lower()
        return any(keyword in lowered for keyword in self.keywords)


def call_text_model(prompt: str) -> str:
    provider = LLM_PROVIDER.lower().strip()
    if provider == "cometapi":
        return _call_comet_text_model(prompt)
    if provider == "google":
        return _call_google_text_model(prompt)
    if provider == "ollama":
        return _call_ollama_text_model(prompt)
    raise RuntimeError(f"Unsupported LLM provider '{LLM_PROVIDER}'")


def call_vision_model(image_path: str, prompt: str) -> str:
    provider = LLM_PROVIDER.lower().strip()
    if provider == "cometapi":
        return _call_comet_vision_model(image_path, prompt)
    if provider == "google":
        return _call_google_vision_model(image_path, prompt)
    if provider == "ollama":
        return call_llava(image_path, prompt)
    raise RuntimeError(f"Unsupported vision provider '{LLM_PROVIDER}'")


def call_llava(image_path: str, prompt: str) -> str:
    if not USE_VISION:
        raise RuntimeError("Vision is disabled in config.py")

    print("[MODEL USED] LLaVA")
    print("[MODEL] Using LLaVA (VISION)")
    app_logger.info("[MODEL USED] LLaVA")
    app_logger.info(f"LLaVA image path: {image_path}")
    app_logger.llm_request(prompt)
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [_encode_image(image_path)],
        "stream": False,
        "keep_alive": "0s" if AUTO_UNLOAD_VISION else "5m",
    }
    data = _post_generate(payload)
    parsed = _parse_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)

    if AUTO_UNLOAD_VISION:
        print("[MODEL] Unloading LLaVA to save RAM")
        app_logger.info("[MODEL] Unloading LLaVA to save RAM")
        unload_model(VISION_MODEL)

    return parsed


def _call_comet_vision_model(image_path: str, prompt: str) -> str:
    api_key = os.getenv(COMET_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Missing CometAPI key. Set the environment variable '{COMET_API_KEY_ENV}' before running PraSush."
        )

    print("[MODEL USED] CometAPI Vision")
    print(f"[MODEL] Using CometAPI vision ({COMET_MODEL})")
    app_logger.info(f"[MODEL USED] CometAPI Vision ({COMET_MODEL})")
    app_logger.info(f"Vision image path: {image_path}")
    app_logger.llm_request(prompt)

    image_b64 = _encode_image(image_path)
    payload = {
        "model": COMET_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are PraSush, a personal ambient AI assistant. Follow the prompt instructions carefully.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            },
        ],
        "temperature": 0.5,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(f"{COMET_API_ENDPOINT}/chat/completions", headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] CometAPI vision request failed: {exc}")
        app_logger.error(f"CometAPI vision request failed: {exc}")
        raise RuntimeError(f"CometAPI vision request failed: {exc}") from exc

    parsed = _parse_comet_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_google_vision_model(image_path: str, prompt: str) -> str:
    api_key = os.getenv(GOOGLE_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Missing Google API key. Set the environment variable '{GOOGLE_API_KEY_ENV}' before running PraSush."
        )

    print("[MODEL USED] Google Gemini Vision")
    print(f"[MODEL] Using Google Gemini vision ({GOOGLE_MODEL})")
    app_logger.info(f"[MODEL USED] Google Gemini Vision ({GOOGLE_MODEL})")
    app_logger.info(f"Vision image path: {image_path}")
    app_logger.llm_request(prompt)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": _encode_image(image_path),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 512,
        },
    }
    url = f"{GOOGLE_API_ENDPOINT}/{GOOGLE_MODEL}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] Google vision request failed: {exc}")
        app_logger.error(f"Google vision request failed: {exc}")
        raise RuntimeError(f"Google vision request failed: {exc}") from exc

    parsed = _parse_google_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_google_text_model(prompt: str) -> str:
    api_key = os.getenv(GOOGLE_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Missing Google API key. Set the environment variable '{GOOGLE_API_KEY_ENV}' before running PraSush."
        )

    print("[MODEL USED] Google Gemini")
    print(f"[MODEL] Using Google Gemini ({GOOGLE_MODEL})")
    app_logger.info(f"[MODEL USED] Google Gemini ({GOOGLE_MODEL})")
    app_logger.llm_request(prompt)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 512,
        },
    }
    url = f"{GOOGLE_API_ENDPOINT}/{GOOGLE_MODEL}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] Google AI Studio request failed: {exc}")
        app_logger.error(f"Google AI Studio request failed: {exc}")
        raise RuntimeError(f"Google AI Studio request failed: {exc}") from exc

    parsed = _parse_google_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_comet_text_model(prompt: str) -> str:
    api_key = os.getenv(COMET_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Missing CometAPI key. Set the environment variable '{COMET_API_KEY_ENV}' before running PraSush."
        )

    print("[MODEL USED] CometAPI")
    print(f"[MODEL] Using CometAPI ({COMET_MODEL})")
    app_logger.info(f"[MODEL USED] CometAPI ({COMET_MODEL})")
    app_logger.llm_request(prompt)

    payload = {
        "model": COMET_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are PraSush, a personal ambient AI assistant. Follow the prompt instructions carefully.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(f"{COMET_API_ENDPOINT}/chat/completions", headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] CometAPI request failed: {exc}")
        app_logger.error(f"CometAPI request failed: {exc}")
        raise RuntimeError(f"CometAPI request failed: {exc}") from exc

    parsed = _parse_comet_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_ollama_text_model(prompt: str) -> str:
    print("[MODEL USED] Ollama Phi-3")
    print("[MODEL] Using Phi3 via Ollama")
    app_logger.info("[MODEL USED] Ollama Phi-3")
    app_logger.llm_request(prompt)
    payload = {
        "model": OLLAMA_TEXT_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    data = _post_generate(payload)
    parsed = _parse_ollama_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def unload_model(model_name: str) -> None:
    payload = {
        "model": model_name,
        "keep_alive": 0,
    }
    try:
        requests.post(f"{OLLAMA_ENDPOINT}/generate", json=payload, timeout=30).raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERROR] Failed to unload model '{model_name}': {exc}")
        app_logger.error(f"Failed to unload model '{model_name}': {exc}")


def _post_generate(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(f"{OLLAMA_ENDPOINT}/generate", json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Ollama returned a non-dictionary response.")
        return data
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"[ERROR] Ollama request failed: {exc}")
        app_logger.error(f"Ollama request failed: {exc}")
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def _parse_ollama_response(data: dict[str, Any]) -> str:
    parsed = str(data.get("response", "")).strip()
    if not parsed:
        raise RuntimeError("Ollama response did not include a 'response' field.")
    return parsed


def _parse_google_response(data: dict[str, Any]) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Google response did not include any candidates.")

    first = candidates[0]
    content = first.get("content", {})
    parts = content.get("parts", [])
    if not isinstance(parts, list):
        raise RuntimeError("Google response content parts were invalid.")

    texts = [str(part.get("text", "")).strip() for part in parts if isinstance(part, dict) and part.get("text")]
    parsed = "\n".join(texts).strip()
    if not parsed:
        raise RuntimeError("Google response did not include text output.")
    return parsed


def _parse_comet_response(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("CometAPI response did not include choices.")

    first = choices[0]
    message = first.get("message", {}) if isinstance(first, dict) else {}
    parsed = str(message.get("content", "")).strip()
    if not parsed:
        raise RuntimeError("CometAPI response did not include assistant content.")
    return parsed


def _encode_image(image_path: str) -> str:
    image_bytes = Path(image_path).read_bytes()
    return base64.b64encode(image_bytes).decode("utf-8")

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import requests

from config import AUTO_UNLOAD_VISION, OLLAMA_ENDPOINT, PHI3_MODEL, USE_VISION, VISION_KEYWORDS, VISION_MODEL


class VisionKeywordRouter:
    def __init__(self, keywords: list[str] | None = None) -> None:
        self.keywords = [keyword.lower() for keyword in (keywords or VISION_KEYWORDS)]

    def is_visual_query(self, query: str) -> bool:
        lowered = query.lower()
        return any(keyword in lowered for keyword in self.keywords)


def call_phi3(prompt: str) -> str:
    print("[MODEL USED] Phi-3")
    print("[MODEL] Using Phi3")
    payload = {
        "model": PHI3_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    data = _post_generate(payload)
    parsed = _parse_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    return parsed


def call_llava(image_path: str, prompt: str) -> str:
    if not USE_VISION:
        raise RuntimeError("Vision is disabled in config.py")

    print("[MODEL USED] LLaVA")
    print("[MODEL] Using LLaVA (VISION)")
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

    if AUTO_UNLOAD_VISION:
        print("[MODEL] Unloading LLaVA to save RAM")
        unload_model(VISION_MODEL)

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
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def _parse_response(data: dict[str, Any]) -> str:
    parsed = str(data.get("response", "")).strip()
    if not parsed:
        raise RuntimeError("Ollama response did not include a 'response' field.")
    return parsed


def _encode_image(image_path: str) -> str:
    image_bytes = Path(image_path).read_bytes()
    return base64.b64encode(image_bytes).decode("utf-8")

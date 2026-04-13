from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config import (
    AUTO_UNLOAD_VISION,
    COMET_API_ENDPOINT,
    COMET_API_KEY_ENV,
    COMET_MODEL,
    GOOGLE_API_ENDPOINT,
    GOOGLE_API_KEY_ENV,
    GOOGLE_MODEL,
    LLM_PROVIDER,
    NVIDIA_API_ENDPOINT,
    NVIDIA_API_KEY_ENV,
    NVIDIA_TEXT_MODEL,
    NVIDIA_VISION_MODEL,
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
    if provider == "nvidia":
        return _call_nvidia_text_model(prompt)
    if provider == "cometapi":
        return _call_comet_text_model(prompt)
    if provider == "google":
        return _call_google_text_model(prompt)
    if provider == "ollama":
        return _call_ollama_text_model(prompt)
    raise RuntimeError(f"Unsupported LLM provider '{LLM_PROVIDER}'")


def call_vision_model(image_path: str, prompt: str) -> str:
    provider = LLM_PROVIDER.lower().strip()
    if provider == "nvidia":
        return _call_nvidia_vision_model(image_path, prompt)
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
    parsed = _parse_ollama_response(data)
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
    api_key = _get_secret(COMET_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            _missing_key_message("CometAPI key", COMET_API_KEY_ENV)
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
    data = _execute_comet_chat_completion(api_key=api_key, payload=payload, request_label="CometAPI vision")

    parsed = _parse_comet_response(data)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_nvidia_vision_model(image_path: str, prompt: str) -> str:
    api_key = _get_secret(NVIDIA_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(_missing_key_message("NVIDIA API key", NVIDIA_API_KEY_ENV))

    print("[MODEL USED] NVIDIA Vision")
    print(f"[MODEL] Using NVIDIA vision ({NVIDIA_VISION_MODEL})")
    app_logger.info(f"[MODEL USED] NVIDIA Vision ({NVIDIA_VISION_MODEL})")
    app_logger.info(f"Vision image path: {image_path}")
    app_logger.llm_request(prompt)

    image_b64 = _encode_image(image_path)
    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are PraSush, a bilingual visual assistant. "
                    "The user may ask visual questions in Hindi, Hinglish, or English. "
                    "You must understand the user's intent regardless of language and reply in the same language style requested by the prompt. "
                    "Never claim that you cannot answer only because the question is in Hindi or Hinglish."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            },
        ],
        "temperature": 0.4,
        "max_tokens": 512,
    }
    data = _execute_openai_compatible_chat_completion(
        api_key=api_key,
        base_url=NVIDIA_API_ENDPOINT,
        payload=payload,
        request_label="NVIDIA vision",
        key_env_name=NVIDIA_API_KEY_ENV,
    )

    parsed = _parse_comet_response(data)
    parsed = _repair_low_quality_reply(parsed, prompt, api_key, NVIDIA_API_ENDPOINT, NVIDIA_VISION_MODEL, NVIDIA_API_KEY_ENV)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_google_vision_model(image_path: str, prompt: str) -> str:
    api_key = _get_secret(GOOGLE_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            _missing_key_message("Google API key", GOOGLE_API_KEY_ENV)
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
    api_key = _get_secret(GOOGLE_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            _missing_key_message("Google API key", GOOGLE_API_KEY_ENV)
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


def _call_nvidia_text_model(prompt: str) -> str:
    api_key = _get_secret(NVIDIA_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(_missing_key_message("NVIDIA API key", NVIDIA_API_KEY_ENV))

    print("[MODEL USED] NVIDIA")
    print(f"[MODEL] Using NVIDIA ({NVIDIA_TEXT_MODEL})")
    app_logger.info(f"[MODEL USED] NVIDIA ({NVIDIA_TEXT_MODEL})")
    app_logger.llm_request(prompt)

    payload = {
        "model": NVIDIA_TEXT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are PraSush, a bilingual personal ambient AI assistant. "
                    "Detect Hindi, English, or Hinglish and reply in the same language or mix. "
                    "Never say that you cannot answer in Hindi. "
                    "When the user asks a normal informational question, answer it directly."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.6,
        "max_tokens": 512,
    }
    data = _execute_openai_compatible_chat_completion(
        api_key=api_key,
        base_url=NVIDIA_API_ENDPOINT,
        payload=payload,
        request_label="NVIDIA",
        key_env_name=NVIDIA_API_KEY_ENV,
    )

    parsed = _parse_comet_response(data)
    parsed = _repair_low_quality_reply(parsed, prompt, api_key, NVIDIA_API_ENDPOINT, NVIDIA_TEXT_MODEL, NVIDIA_API_KEY_ENV)
    print(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    print(f"[PARSED RESPONSE] {parsed}")
    app_logger.debug(f"[RAW RESPONSE] {json.dumps(data, ensure_ascii=False)}")
    app_logger.llm_response(parsed)
    return parsed


def _call_comet_text_model(prompt: str) -> str:
    api_key = _get_secret(COMET_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            _missing_key_message("CometAPI key", COMET_API_KEY_ENV)
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
    data = _execute_comet_chat_completion(api_key=api_key, payload=payload, request_label="CometAPI")

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


def _execute_comet_chat_completion(api_key: str, payload: dict[str, Any], request_label: str) -> dict[str, Any]:
    return _execute_openai_compatible_chat_completion(
        api_key=api_key,
        base_url=COMET_API_ENDPOINT,
        payload=payload,
        request_label=request_label,
        key_env_name=COMET_API_KEY_ENV,
    )


def _execute_openai_compatible_chat_completion(
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    request_label: str,
    key_env_name: str,
) -> dict[str, Any]:
    if OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(**payload)
            return response.model_dump()
        except Exception as exc:
            print(f"[ERROR] {request_label} SDK request failed: {exc}")
            app_logger.error(f"{request_label} SDK request failed: {exc}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response: requests.Response | None = None
    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        raise RuntimeError(_format_openai_compatible_http_error(response, payload.get("model"), key_env_name)) from exc
    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] {request_label} request failed: {exc}")
        app_logger.error(f"{request_label} request failed: {exc}")
        raise RuntimeError(f"{request_label} request failed: {exc}") from exc


def _format_openai_compatible_http_error(
    response: requests.Response | None, model_name: Any, key_env_name: str
) -> str:
    status_code = response.status_code if response is not None else "unknown"
    reason = response.reason if response is not None else "Unknown"
    body_preview = ""
    quota_hint = ""
    if response is not None:
        text = response.text.strip()
        if text:
            body_preview = f" Response body: {text[:300]}"
            try:
                parsed = response.json()
            except ValueError:
                parsed = {}
            error_block = parsed.get("error", {}) if isinstance(parsed, dict) else {}
            if error_block.get("code") == "insufficient_user_quota":
                quota_hint = (
                    " Your current provider account has no remaining quota, so no model call can succeed until "
                    "you add credits or switch to another available provider."
                )
    hint = (
        f"Check that {key_env_name} is valid, that model '{model_name}' is enabled for your account, "
        "and that the request is using Authorization: Bearer <key>."
    )
    message = f"Provider request failed: {status_code} {reason}.{quota_hint} {hint}{body_preview}"
    safe_message = _sanitize_text(message)
    _safe_print(f"[ERROR] {safe_message}")
    app_logger.error(safe_message)
    return safe_message


def _missing_key_message(label: str, env_name: str) -> str:
    return (
        f"Missing {label}. Set '{env_name}' in the current shell, store it in a local .env file, "
        "or define it in the Windows User or Machine environment variables."
    )


def _get_secret(env_name: str) -> str:
    value = os.getenv(env_name, "").strip()
    if value:
        return value

    env_file_values = _read_dotenv_values()
    value = env_file_values.get(env_name, "").strip()
    if value:
        os.environ[env_name] = value
        return value

    if os.name == "nt":
        for scope in ("User", "Machine"):
            value = _read_windows_env_var(env_name, scope).strip()
            if value:
                os.environ[env_name] = value
                return value

    return ""


def _read_dotenv_values() -> dict[str, str]:
    results: dict[str, str] = {}
    for filename in (".env", ".env.local"):
        path = Path(filename)
        if not path.exists():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cleaned = value.strip().strip("'").strip('"')
                results[key.strip()] = cleaned
        except OSError as exc:
            app_logger.warning(f"Failed to read {filename}: {exc}")
    return results


def _read_windows_env_var(env_name: str, scope: str) -> str:
    try:
        import winreg
    except ImportError:
        return ""

    scope_map = {
        "User": (winreg.HKEY_CURRENT_USER, r"Environment"),
        "Machine": (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
    }
    registry_root, subkey = scope_map[scope]

    try:
        with winreg.OpenKey(registry_root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, env_name)
            return str(value)
    except OSError:
        return ""


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        fallback = message.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(fallback)


def _sanitize_text(value: str) -> str:
    return value.encode("ascii", errors="backslashreplace").decode("ascii")


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


def _repair_low_quality_reply(
    parsed: str,
    prompt: str,
    api_key: str,
    base_url: str,
    model_name: str,
    key_env_name: str,
) -> str:
    if not _looks_like_low_quality_reply(parsed):
        return parsed

    repair_prompt = (
        f"{prompt}\n\n"
        "Important recovery instruction: The previous answer was low-quality, generic, or incorrectly claimed "
        "an inability to answer in Hindi. Answer the user's actual question directly now. "
        "Do not mention language limitations. Do not give availability filler. "
        "Do not say that you can provide information; provide the concrete answer itself in 3 to 6 natural spoken sentences."
    )
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "Recover from a poor previous answer and answer the user's actual question directly.",
            },
            {
                "role": "user",
                "content": repair_prompt,
            },
        ],
        "temperature": 0.3,
        "max_tokens": 512,
    }

    try:
        repaired = _execute_openai_compatible_chat_completion(
            api_key=api_key,
            base_url=base_url,
            payload=payload,
            request_label="Recovery",
            key_env_name=key_env_name,
        )
        repaired_text = _parse_comet_response(repaired)
        if repaired_text.strip():
            app_logger.info("Recovered low-quality model reply with a stricter retry.")
            return repaired_text
    except RuntimeError as exc:
        app_logger.warning(f"Recovery retry failed: {exc}")

    return parsed


def _looks_like_low_quality_reply(parsed: str) -> bool:
    normalized = " ".join(parsed.lower().split())
    direct_markers = (
        "cannot answer in hindi",
        "can't answer in hindi",
        "i cannot answer in hindi",
        "i am available",
        "i can provide information",
        "i can tell you about",
        "उपलब्ध हूँ",
        "हिंदी में प्रश्नों का उत्तर नहीं दे सकता",
        "मेरे पास आपके लिए कोई जवाब नहीं है",
        "मैं आपको जानकारी दे सकता",
        "मैं आपको बता सकता",
    )
    if any(marker in normalized for marker in direct_markers):
        return True

    if len(parsed.strip()) < 40 and ("?" not in parsed and "!" not in parsed):
        vague_short_replies = (
            "मैं ठीक हूँ",
            "ठीक है",
            "sure,",
            "okay,",
        )
        if any(marker in normalized for marker in vague_short_replies):
            return True

    generic_reply_patterns = (
        r"^i can (tell|provide|help).{0,80}$",
        r"^i can answer.{0,80}$",
        r"^मैं आपको .{0,80} के बारे में .{0,40} दे सकता .*$",
    )
    return any(re.match(pattern, normalized) for pattern in generic_reply_patterns)


def _encode_image(image_path: str) -> str:
    image_bytes = Path(image_path).read_bytes()
    return base64.b64encode(image_bytes).decode("utf-8")

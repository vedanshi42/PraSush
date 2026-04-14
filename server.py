from __future__ import annotations

import base64
import os
import re
import tempfile
from typing import Any, Optional

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from llm.client import call_text_model, call_vision_model
from logger import app_logger

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

DATA_URL_PATTERN = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$")


def _parse_image_data(image_data: str) -> bytes:
    match = DATA_URL_PATTERN.match(image_data)
    if match:
        image_b64 = match.group("data")
    else:
        image_b64 = image_data
    return base64.b64decode(image_b64)


def _build_openai_compatible_payload(
    model: str,
    prompt: str,
    image_data: Optional[str] = None,
) -> dict[str, Any]:
    if image_data:
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are PraSush, a bilingual visual assistant. "
                        "Answer visual questions in the same language "
                        "as the user."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    "data:image/jpeg;base64,"
                                    f"{image_data}"
                                )
                            },
                        },
                    ],
                },
            ],
            "temperature": 0.4,
            "max_tokens": 320,
        }

    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are PraSush, a fast bilingual ambient AI assistant. "
                    "Reply in the same language as the current user turn. "
                    "Do not drift into another language "
                    "unless the user explicitly asks."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 320,
    }


def _parse_chat_response(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Provider response did not include choices.")

    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("Unexpected response format for choices.")

    message = first.get("message", {})
    content = message.get("content")
    if not isinstance(content, str) or not content:
        content = first.get("content")

    if isinstance(content, str) and content.strip():
        return content.strip()

    reasoning = (
        message.get("reasoning_content")
        or first.get("reasoning_content")
    )
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()

    raise RuntimeError("Provider response did not include assistant content.")


def _prepend_user_name(prompt: str, user_name: str | None) -> str:
    if user_name:
        return f"User name: {user_name}\n\n{prompt}"
    return prompt


def _call_custom_provider(
    api_key: str,
    endpoint: str,
    model: str,
    prompt: str,
    image_data: str | None = None,
) -> str:
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = _build_openai_compatible_payload(
        model=model, prompt=prompt, image_data=image_data
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    app_logger.info(f"[CUSTOM BACKEND] {endpoint} model={model}")

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    app_logger.debug(f"[CUSTOM BACKEND RAW] {data}")
    return _parse_chat_response(data)


@app.route("/api/status", methods=["GET"])
def api_status() -> Any:
    return jsonify({"status": "ok", "message": "PraSush backend is running."})


@app.route("/api/chat", methods=["POST"])
def api_chat() -> Any:
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "JSON payload is required."}), 400

    query = str(payload.get("query", "")).strip()
    if not query:
        return jsonify({"error": "The 'query' field is required."}), 400

    user_name = str(payload.get("user_name", "")).strip() or None
    image_data = payload.get("image_data")
    custom = bool(payload.get("custom"))
    provider_settings = payload.get("provider_settings") if custom else None

    try:
        if custom:
            if not isinstance(provider_settings, dict):
                raise ValueError(
                    "provider_settings must be an object for custom mode."
                )

            endpoint = str(provider_settings.get("endpoint", "")).strip()
            model = str(provider_settings.get("model", "")).strip()
            api_key = str(provider_settings.get("api_key", "")).strip()
            if not endpoint or not model or not api_key:
                raise ValueError(
                    "Custom provider settings require endpoint, "
                    "model, and api_key."
                )

            if image_data:
                image_data = _parse_image_data(str(image_data))
                image_data = base64.b64encode(image_data).decode("utf-8")
            prompt = _prepend_user_name(query, user_name)
            response_text = _call_custom_provider(
                api_key=api_key,
                endpoint=endpoint,
                model=model,
                prompt=prompt,
                image_data=image_data,
            )

        else:
            if image_data:
                image_bytes = _parse_image_data(str(image_data))
                with tempfile.NamedTemporaryFile(
                    suffix=".jpg",
                    delete=False,
                ) as tmp_file:
                    tmp_file.write(image_bytes)
                    temp_path = tmp_file.name
                try:
                    prompt = _prepend_user_name(query, user_name)
                    response_text = call_vision_model(temp_path, prompt)
                finally:
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
            else:
                prompt = _prepend_user_name(query, user_name)
                response_text = call_text_model(prompt)

        return jsonify({"response": response_text})

    except Exception as exc:
        app_logger.exception("Failed to process chat request")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

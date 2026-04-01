import os
import requests


class OllamaClient:
    def __init__(self, model="llama2", host=None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = model
        self.endpoint = f"{self.host}/completions"

    def ask(self, prompt, max_tokens=400, temperature=0.6):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            response = requests.post(self.endpoint, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("choices"):
                choice = data["choices"][0]
                if isinstance(choice, dict):
                    return (
                        choice.get("message", {}).get("content")
                        or choice.get("text")
                        or ""
                    ).strip()
            return str(data)
        except Exception as exc:
            print(f"LLM request failed: {exc}")
            return ""

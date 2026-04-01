import os
import requests


class OllamaClient:
    def __init__(self, model="phi3", host=None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = model
        self.endpoint = f"{self.host}/api/generate"

    def ask(self, prompt, max_tokens=400, temperature=0.6):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            response = requests.post(self.endpoint, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "response" in data:
                return data["response"].strip()
            return str(data)
        except Exception as exc:
            print(f"LLM request failed: {exc}")
            return ""

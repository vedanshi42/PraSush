import json
import os


class MemoryStore:
    def __init__(self, file_path=None, max_items=5):
        self.file_path = file_path or os.path.join(os.path.dirname(__file__), "history.json")
        self.max_items = max_items
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, list):
                        return data[-self.max_items:]
            except Exception:
                pass
        return []

    def add_interaction(self, role, text):
        entry = {"role": role, "text": text}
        self.history.append(entry)
        self.history = self.history[-self.max_items :]
        self._save_history()

    def _save_history(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as handle:
                json.dump(self.history, handle, indent=2)
        except Exception:
            pass

    def get_context(self):
        if not self.history:
            return ""
        lines = []
        for item in self.history:
            role = item.get("role", "user")
            text = item.get("text", "")
            lines.append(f"{role.capitalize()}: {text}")
        return "\n".join(lines)

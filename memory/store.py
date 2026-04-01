import json
import os
from logger import app_logger


class MemoryStore:
    def __init__(self, file_path=None, max_items=5):
        self.file_path = file_path or os.path.join(os.path.dirname(__file__), "history.json")
        self.max_items = max_items
        self.history = self._load_history()
        app_logger.info(f"Memory store initialized with max {max_items} items. Current history: {len(self.history)} items")

    def _load_history(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, list):
                        recent = data[-self.max_items:]
                        app_logger.debug(f"Loaded {len(recent)} recent interactions from history")
                        return recent
            except Exception as e:
                app_logger.error(f"Error loading memory: {e}")
        return []

    def add_interaction(self, role, text):
        entry = {"role": role, "text": text}
        self.history.append(entry)
        self.history = self.history[-self.max_items:]
        self._save_history()
        app_logger.debug(f"Added interaction - {role}: {text[:50]}..." if len(text) > 50 else f"Added interaction - {role}: {text}")

    def _save_history(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as handle:
                json.dump(self.history, handle, indent=2)
            app_logger.debug(f"Saved memory with {len(self.history)} items")
        except Exception as e:
            app_logger.error(f"Error saving memory: {e}")

    def get_context(self):
        if not self.history:
            return ""
        lines = []
        for item in self.history:
            role = item.get("role", "user")
            text = item.get("text", "")
            lines.append(f"{role.capitalize()}: {text}")
        context = "\n".join(lines)
        app_logger.debug(f"Memory context: {context[:100]}...")
        return context

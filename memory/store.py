from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from config import MAX_MEMORY_CONTEXT, MEMORY_PATH
from logger import app_logger


@dataclass
class Exchange:
    user: str
    assistant: str


class MemoryStore:
    def __init__(self, file_path: Path | None = None, max_items: int = MAX_MEMORY_CONTEXT) -> None:
        self.file_path = file_path or MEMORY_PATH
        self.max_items = max_items
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()

    def add_exchange(self, user_text: str, assistant_text: str) -> None:
        self.history.append(Exchange(user=user_text, assistant=assistant_text))
        self.history = self.history[-self.max_items :]
        self._save_history()

    def get_context_block(self, max_chars: int = 500) -> str:
        if not self.history:
            return "No previous context."

        lines: list[str] = []
        for index, item in enumerate(self.history[-self.max_items :], start=1):
            user_text = " ".join(item.user.split())[:120]
            assistant_text = " ".join(item.assistant.split())[:180]
            lines.append(f"{index}. User: {user_text}")
            lines.append(f"{index}. Assistant: {assistant_text}")
        compact = " ".join(lines)
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3] + "..."

    def _load_history(self) -> list[Exchange]:
        if not self.file_path.exists():
            return []
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            app_logger.error(f"Failed to load memory history: {exc}")
            return []

        if not isinstance(raw, list):
            app_logger.error("Memory history format is invalid.")
            return []

        history: list[Exchange] = []
        for item in raw[-self.max_items :]:
            if not isinstance(item, dict):
                continue
            user = str(item.get("user", "")).strip()
            assistant = str(item.get("assistant", "")).strip()
            if user or assistant:
                history.append(Exchange(user=user, assistant=assistant))
        return history

    def _save_history(self) -> None:
        serialized = [asdict(item) for item in self.history[-self.max_items :]]
        try:
            self.file_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
        except OSError as exc:
            app_logger.error(f"Failed to save memory history: {exc}")

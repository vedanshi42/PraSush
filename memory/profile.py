from __future__ import annotations

import json
from pathlib import Path

from config import PROFILE_PATH
from logger import app_logger


class UserProfileStore:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or PROFILE_PATH
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def get_name(self) -> str:
        return str(self.data.get("name", "")).strip()

    def set_name(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            return
        self.data["name"] = cleaned
        self._save()

    def _load(self) -> dict[str, str]:
        if not self.file_path.exists():
            return {}
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            app_logger.error(f"Failed to load user profile: {exc}")
            return {}
        return raw if isinstance(raw, dict) else {}

    def _save(self) -> None:
        try:
            self.file_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except OSError as exc:
            app_logger.error(f"Failed to save user profile: {exc}")

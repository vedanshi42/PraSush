from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import re
import uuid
from pathlib import Path


@dataclass
class Reminder:
    id: str
    message: str
    due_at: str
    spoken: bool = False

    @property
    def due_datetime(self) -> datetime:
        return datetime.fromisoformat(self.due_at)


class ReminderStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.reminders = self._load()

    def add(self, message: str, due_at: datetime) -> Reminder:
        reminder = Reminder(
            id=str(uuid.uuid4()),
            message=message.strip(),
            due_at=due_at.isoformat(),
            spoken=False,
        )
        self.reminders.append(reminder)
        self._save()
        return reminder

    def get_due(self, now: datetime) -> list[Reminder]:
        return [reminder for reminder in self.reminders if not reminder.spoken and reminder.due_datetime <= now]

    def mark_spoken(self, reminder_id: str) -> None:
        for reminder in self.reminders:
            if reminder.id == reminder_id:
                reminder.spoken = True
                self._save()
                return

    def _load(self) -> list[Reminder]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        reminders: list[Reminder] = []
        for item in data if isinstance(data, list) else []:
            if isinstance(item, dict):
                try:
                    reminders.append(Reminder(**item))
                except TypeError:
                    continue
        return reminders

    def _save(self) -> None:
        payload = [asdict(reminder) for reminder in self.reminders]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_reminder_request(text: str, now: datetime) -> tuple[datetime | None, str]:
    original = re.sub(r"\s+", " ", text.strip())
    lowered = original.lower()

    day_offset = 0
    if "day after tomorrow" in lowered:
        day_offset = 2
        lowered = lowered.replace("day after tomorrow", " ")
    elif "tomorrow" in lowered:
        day_offset = 1
        lowered = lowered.replace("tomorrow", " ")
    elif "today" in lowered:
        lowered = lowered.replace("today", " ")

    default_hour = None
    if "morning" in lowered:
        default_hour = 9
        lowered = lowered.replace("morning", " ")
    elif "afternoon" in lowered:
        default_hour = 15
        lowered = lowered.replace("afternoon", " ")
    elif "evening" in lowered:
        default_hour = 19
        lowered = lowered.replace("evening", " ")
    elif "tonight" in lowered:
        default_hour = 20
        lowered = lowered.replace("tonight", " ")

    hour = None
    minute = 0
    time_match = re.search(r"\b(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lowered)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or "0")
        meridiem = (time_match.group(3) or "").lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        lowered = lowered.replace(time_match.group(0), " ")
    elif default_hour is not None:
        hour = default_hour

    if hour is None:
        return None, ""

    due_date = (now + timedelta(days=day_offset)).date()
    due_at = datetime.combine(due_date, datetime.min.time(), tzinfo=now.tzinfo).replace(hour=hour, minute=minute)
    if due_at <= now and day_offset == 0:
        due_at += timedelta(days=1)

    message = original
    cleanup_patterns = [
        r"\bremind me to\b",
        r"\bset (?:me )?a reminder(?: to)?\b",
        r"\bcreate (?:me )?a reminder(?: to)?\b",
        r"\bplease\b",
        r"\btomorrow\b",
        r"\btoday\b",
        r"\bday after tomorrow\b",
        r"\bmorning\b",
        r"\bafternoon\b",
        r"\bevening\b",
        r"\btonight\b",
        r"\bat\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    ]
    for pattern in cleanup_patterns:
        message = re.sub(pattern, " ", message, flags=re.IGNORECASE)
    message = re.sub(r"\s+", " ", message).strip(" ,.-")
    return due_at, message or "your task"

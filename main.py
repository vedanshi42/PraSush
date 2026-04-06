from __future__ import annotations

from datetime import datetime
import re
import sys
import time

from config import BASE_DIR, LOCAL_TIMEZONE, REMINDERS_PATH, USE_VISION, WAKE_VARIANTS, WAKE_WORD
from llm.client import VisionKeywordRouter, call_text_model, call_vision_model
from logger import app_logger
from memory.profile import UserProfileStore
from memory.reminders import ReminderStore, parse_reminder_request
from memory.store import MemoryStore
from ui.display import DisplayManager
from vision.camera import CameraInput
from voice.recognizer import VoiceAssistant

GREETING_MESSAGE = "Hello, I am PraSush. I am here with you."
ASK_NAME_MESSAGE = "Before we begin, what should I call you?"
STOP_PHRASES = {"stop", "shut down", "shutdown", "close", "exit", "bye"}
MAX_CONVERSATION_TURNS = 6
FOLLOW_UP_PROMPT = "I'm listening. Ask another question, or say stop."


class PraSushApp:
    def __init__(self) -> None:
        app_logger.info("Initializing PraSush application")
        self.display = DisplayManager()
        self.memory = MemoryStore()
        self.profile = UserProfileStore()
        self.reminders = ReminderStore(REMINDERS_PATH)
        self.voice = VoiceAssistant()
        self.camera = CameraInput()
        self.vision_router = VisionKeywordRouter()
        self.pending_intent: str | None = None

    def run(self) -> None:
        self.display.set_state("idle", "Waiting for wake word", "Say 'Hey PraSush' to begin.")
        app_logger.info("PraSush main loop started")
        try:
            while True:
                self.check_due_reminders()
                self.display.pump_events()
                wake_text = self.voice.listen_for_wakeword()
                if wake_text and self.is_stop_command(wake_text):
                    self.speak_with_presence("speaking", "Speaking", "Okay, shutting down now.")
                    self.shutdown()
                if wake_text and self.is_wake_match(wake_text):
                    app_logger.info(f"Wake word matched from transcript: {wake_text}")
                    self.handle_interaction()
                    time.sleep(0.8)
                self.display.render()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def handle_interaction(self) -> None:
        user_name = self.profile.get_name()
        greeting = f"Hello {user_name}, I am PraSush. I am here with you." if user_name else GREETING_MESSAGE
        self.speak_with_presence("greeting", "Wake word detected", greeting)

        if not user_name:
            self.capture_user_name()
            user_name = self.profile.get_name()

        empty_turns = 0
        for turn in range(MAX_CONVERSATION_TURNS):
            prompt_text = (
                f"What would you like to know, {user_name}?"
                if turn == 0 and user_name
                else FOLLOW_UP_PROMPT
                if turn > 0
                else "What would you like to know?"
            )
            self.display.set_state("listening", "Listening", prompt_text)
            query = self.voice.record_query()
            if not query:
                empty_turns += 1
                app_logger.warning(f"User query transcript was empty during conversation turn {turn + 1}")
                if empty_turns < 2:
                    self.display.set_state("listening", "Listening", "I didn't catch that. Please try again, or say stop.")
                    continue
                self.display.set_state("idle", "Listening timeout", "I will stay quiet for now.")
                return
            empty_turns = 0

            if self.is_stop_command(query):
                farewell = "Okay, shutting down now."
                self.speak_with_presence("speaking", "Speaking", farewell)
                self.shutdown()

            app_logger.info(f"Handling user query: {query}")
            self.display.set_state("thinking", "Thinking", "Analyzing your request...")
            try:
                response = self.answer_query(query)
            except RuntimeError as exc:
                response = f"Request failed: {exc}"
                print(f"[ERROR] {response}")
                app_logger.error(response)
                self.display.set_state("idle", "Request failed", response)
                return

            self.memory.add_exchange(query, response)
            spoken_response = self.prepare_spoken_text(response)
            self.speak_with_presence("speaking", "Speaking", spoken_response)
            if turn < MAX_CONVERSATION_TURNS - 1:
                self.display.set_state("listening", "Listening", FOLLOW_UP_PROMPT)

        self.display.set_state("idle", "Waiting for wake word", "Say 'Hey PraSush' to begin.")

    def answer_query(self, query: str) -> str:
        local_response = self.handle_local_query(query)
        if local_response is not None:
            return local_response

        prompt = self.build_prompt(query, include_vision=False)
        if USE_VISION and self.vision_router.is_visual_query(query):
            try:
                image_path = self.camera.capture_image()
                scene_hint = self.camera.analyze_scene(image_path)
                app_logger.info(f"Vision query detected. Scene image: {image_path}")
                app_logger.info(f"Vision scene hint: {scene_hint}")
            except RuntimeError as exc:
                print(f"[ERROR] Vision capture failed: {exc}")
                app_logger.error(f"Vision capture failed: {exc}")
                raise
            prompt = self.build_prompt(query, include_vision=True, scene_hint=scene_hint)
            return call_vision_model(str(image_path), prompt)
        return call_text_model(prompt)

    def handle_local_query(self, query: str) -> str | None:
        lowered = query.lower().strip()
        if self.pending_intent == "reminder":
            self.pending_intent = None
            return self.create_reminder_response(query)

        if self.is_time_question(lowered):
            now = datetime.now().astimezone()
            return f"It is {now.strftime('%I:%M %p')} for us right now."

        if self.is_date_question(lowered):
            now = datetime.now().astimezone()
            return f"Today is {now.strftime('%A, %d %B %Y')}."

        if self.is_reminder_request(lowered):
            due_at, message = parse_reminder_request(query, datetime.now().astimezone())
            if due_at and message:
                reminder = self.reminders.add(message, due_at)
                app_logger.info(f"Reminder created: {reminder.message} at {reminder.due_at}")
                return self.format_reminder_confirmation(reminder.message, due_at)
            self.pending_intent = "reminder"
            return "Yes, I can set a reminder. Tell me what to remind you about and when."

        return None

    def create_reminder_response(self, query: str) -> str:
        due_at, message = parse_reminder_request(query, datetime.now().astimezone())
        if not due_at:
            self.pending_intent = "reminder"
            return "I did not catch the reminder time. Please say it like tomorrow at 8 AM, remind me to call mom."
        reminder = self.reminders.add(message, due_at)
        app_logger.info(f"Reminder created: {reminder.message} at {reminder.due_at}")
        return self.format_reminder_confirmation(reminder.message, due_at)

    def format_reminder_confirmation(self, message: str, due_at: datetime) -> str:
        return (
            f"Done. I will remind you to {message} on "
            f"{due_at.strftime('%A, %d %B')} at {due_at.strftime('%I:%M %p')}."
        )

    def check_due_reminders(self) -> None:
        now = datetime.now().astimezone()
        for reminder in self.reminders.get_due(now):
            announcement = f"Reminder. It is time to {reminder.message}."
            app_logger.info(f"Reminder due: {reminder.message}")
            self.speak_with_presence("speaking", "Reminder", announcement)
            self.reminders.mark_spoken(reminder.id)

    def build_prompt(self, query: str, include_vision: bool, scene_hint: str = "") -> str:
        context = self.memory.get_context_block()
        user_name = self.profile.get_name() or "unknown"
        runtime_context = self.build_runtime_context()
        prompt_lines = [
            "You are PraSush, a personal ambient AI assistant with voice, memory, and optional vision.",
            "PraSush is your name only. Do not reinterpret it as a blog, brand, recipe, company, acronym, or anything else.",
            "Be concise, helpful, warm, and conversational. Refer to yourself as PraSush when asked your name.",
            "Answer in natural spoken sentences. Avoid markdown, bullet lists, and repeated 'User query' / 'Assistant' labels in the answer.",
            f"Known user name: {user_name}",
            runtime_context,
            f"Previous context: {context}",
            f"Vision enabled for this turn: {'yes' if include_vision else 'no'}",
            "If vision is enabled, assume the latest camera image represents what you can currently see.",
            "When answering visual questions, mention whether you see a person or face, and mention notable nearby objects if visible.",
            "Do not claim biometric identity recognition. You may say you can see the user if a person is visible.",
            f"User query: {query}",
            "Assistant:",
        ]
        if scene_hint:
            prompt_lines.insert(-2, f"Camera analysis hint: {scene_hint}")
        return "\n".join(prompt_lines)

    def build_runtime_context(self) -> str:
        now = datetime.now().astimezone()
        date_text = now.strftime("%A, %d %B %Y")
        time_text = now.strftime("%I:%M %p")
        timezone_name = now.tzname() or LOCAL_TIMEZONE
        workspace_text = str(BASE_DIR)
        return (
            f"Current runtime context: Date: {date_text}. "
            f"Time: {time_text}. "
            f"Timezone: {timezone_name}. "
            f"Preferred timezone label: {LOCAL_TIMEZONE}. "
            f"Workspace location: {workspace_text}. "
            "Use this runtime context when answering questions about today's date, current time, timezone, or where we are in the current app session. "
            "If the user asks where we are, answer using the workspace location unless they clearly mean a real-world geographic location."
        )

    def capture_user_name(self) -> None:
        self.speak_with_presence("greeting", "Getting to know you", ASK_NAME_MESSAGE)
        self.display.set_state("listening", "Listening for your name", "Tell me your name.")
        spoken_name = self.voice.record_query()
        parsed_name = self.extract_name(spoken_name)
        if not parsed_name:
            fallback = "I will remember your name once I hear it clearly."
            print("[ERROR] Could not parse user name from onboarding response.")
            self.speak_with_presence("speaking", "Speaking", fallback)
            return

        self.profile.set_name(parsed_name)
        confirmation = f"Nice to meet you, {parsed_name}. I will remember your name."
        self.speak_with_presence("speaking", "Speaking", confirmation)

    def speak_with_presence(self, state: str, status_text: str, message: str) -> None:
        self.display.set_state(state, status_text, message)
        self.voice.start_speaking(message)
        while self.voice.is_speaking():
            self.display.pump_events()
            self.display.render()
            time.sleep(0.03)
        self.voice.wait_until_done()
        self.display.render()

    def extract_name(self, spoken_text: str) -> str:
        if not spoken_text:
            return ""
        cleaned = spoken_text.strip()
        patterns = [
            r"\bmy name is ([A-Za-z][A-Za-z'\- ]{0,40})",
            r"\bi am ([A-Za-z][A-Za-z'\- ]{0,40})",
            r"\bi'm ([A-Za-z][A-Za-z'\- ]{0,40})",
            r"\bcall me ([A-Za-z][A-Za-z'\- ]{0,40})",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return self.normalize_name(match.group(1))
        if len(cleaned.split()) <= 3:
            return self.normalize_name(cleaned)
        return ""

    def normalize_name(self, value: str) -> str:
        letters_only = re.sub(r"[^A-Za-z'\- ]", "", value).strip()
        return " ".join(part.capitalize() for part in letters_only.split()[:3])

    def is_stop_command(self, spoken_text: str) -> bool:
        normalized = " ".join(re.sub(r"[^a-z ]", " ", spoken_text.lower()).split())
        return any(phrase in normalized for phrase in STOP_PHRASES)

    def prepare_spoken_text(self, text: str) -> str:
        cleaned = text.replace("**", "").replace("*", "")
        cleaned = re.sub(r"\bUser query:.*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\bAssistant:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def is_reminder_request(self, lowered: str) -> bool:
        patterns = ("remind me", "set a reminder", "create a reminder", "reminder", "alarm")
        return any(pattern in lowered for pattern in patterns)

    def is_time_question(self, lowered: str) -> bool:
        patterns = ("what time", "current time", "time is it", "tell me the time")
        return any(pattern in lowered for pattern in patterns)

    def is_date_question(self, lowered: str) -> bool:
        patterns = ("what is the date", "today's date", "what day is it", "tell me the date")
        return any(pattern in lowered for pattern in patterns)

    def is_wake_match(self, spoken_text: str) -> bool:
        lowered = spoken_text.lower().strip()
        normalized = re.sub(r"[^a-z ]", " ", lowered)
        normalized = " ".join(normalized.split())

        if WAKE_WORD in normalized:
            return True

        if normalized in {"hi", "hello", "hey"}:
            return True

        if len(normalized.split()) > 3:
            return False

        return any(variant in normalized for variant in WAKE_VARIANTS)

    def shutdown(self) -> None:
        app_logger.info("PraSush shutting down")
        self.camera.close()
        self.display.close()
        sys.exit(0)


if __name__ == "__main__":
    PraSushApp().run()

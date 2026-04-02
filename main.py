from __future__ import annotations

from datetime import datetime
import re
import sys
import time

from config import BASE_DIR, LOCAL_TIMEZONE, USE_VISION, WAKE_VARIANTS, WAKE_WORD
from llm.client import VisionKeywordRouter, call_llava, call_phi3
from logger import app_logger
from memory.profile import UserProfileStore
from memory.store import MemoryStore
from ui.display import DisplayManager
from vision.camera import CameraInput
from voice.recognizer import VoiceAssistant

GREETING_MESSAGE = "Hello, I am PraSush. I am here with you."
ASK_NAME_MESSAGE = "Before we begin, what should I call you?"


class PraSushApp:
    def __init__(self) -> None:
        app_logger.info("Initializing PraSush application")
        self.display = DisplayManager()
        self.memory = MemoryStore()
        self.profile = UserProfileStore()
        self.voice = VoiceAssistant()
        self.camera = CameraInput()
        self.vision_router = VisionKeywordRouter()

    def run(self) -> None:
        self.display.set_state("idle", "Waiting for wake word", "Say 'Hey PraSush' to begin.")
        app_logger.info("PraSush main loop started")
        try:
            while True:
                self.display.pump_events()
                wake_text = self.voice.listen_for_wakeword()
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

        prompt_text = f"What would you like to know, {user_name}?" if user_name else "What would you like to know?"
        self.display.set_state("listening", "Listening", prompt_text)
        query = self.voice.record_query()
        if not query:
            message = "I could not understand the request."
            print(f"[ERROR] {message}")
            app_logger.warning("User query transcript was empty after wake flow")
            self.display.set_state("idle", "Listening timeout", message)
            return

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

        self.speak_with_presence("speaking", "Speaking", response)
        self.display.set_state("idle", "Waiting for wake word", "Say 'Hey PraSush' to begin.")

    def answer_query(self, query: str) -> str:
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
            return call_llava(str(image_path), prompt)
        return call_phi3(prompt)

    def build_prompt(self, query: str, include_vision: bool, scene_hint: str = "") -> str:
        context = self.memory.get_context_block()
        user_name = self.profile.get_name() or "unknown"
        runtime_context = self.build_runtime_context()
        prompt_lines = [
            "You are PraSush, a personal ambient AI assistant with voice, memory, and optional vision.",
            "PraSush is your name only. Do not reinterpret it as a blog, brand, recipe, company, acronym, or anything else.",
            "Be concise, helpful, warm, and conversational. Refer to yourself as PraSush when asked your name.",
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
        self.voice.speak(message)
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

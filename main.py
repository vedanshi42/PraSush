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
from voice.recognizer import SpeechRecognitionResult, VoiceAssistant

GREETING_MESSAGE = "Hello, I am PraSush. I am here with you."
GREETING_MESSAGE_HI = "नमस्ते, मैं प्रसुष हूँ। मैं आपके साथ हूँ।"
ASK_NAME_MESSAGE = "Before we begin, what should I call you?"
ASK_NAME_MESSAGE_HI = "हम शुरू करने से पहले, मैं आपको किस नाम से पुकारूँ?"
STOP_PHRASES = {"stop", "shut down", "shutdown", "close", "exit", "bye"}
HINDI_STOP_PHRASES = {"band", "band karo", "ruk", "ruko", "bas", "बस", "बंद", "बंद करो", "रुको"}
MAX_CONVERSATION_TURNS = 6
FOLLOW_UP_PROMPT = "I'm listening. Ask another question, or say stop."
FOLLOW_UP_PROMPT_HI = "मैं सुन रही हूँ। अगला सवाल पूछिए या रुकने के लिए stop कहिए।"
FOLLOW_UP_MARKERS = {
    "aur",
    "aur batao",
    "aur bataye",
    "aur jankari",
    "continue",
    "go on",
    "tell me more",
    "more details",
    "और",
    "और बताओ",
    "और बताइए",
    "और जानकारी",
}


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
        self.language_lock: str | None = None

    def run(self) -> None:
        self.display.set_state("idle", "Waiting for wake word", "Say hi, hey, or namaste to begin.")
        app_logger.info("PraSush main loop started")
        try:
            while True:
                self.check_due_reminders()
                self.display.pump_events()
                wake_result = self.voice.listen_for_wakeword_result()
                wake_text = wake_result.transcript.lower()
                if wake_text and self.is_stop_command(wake_text):
                    self.speak_with_presence("speaking", "Speaking", "Okay, shutting down now.")
                    self.shutdown()
                if wake_text and self.is_wake_match(wake_text):
                    app_logger.info(f"Wake word matched from transcript: {wake_text}")
                    self.handle_interaction(wake_result)
                    time.sleep(0.5)
                self.display.render()
                time.sleep(0.05)
        except KeyboardInterrupt:
            self.shutdown()

    def handle_interaction(self, wake_result: SpeechRecognitionResult) -> None:
        wake_language = self.get_turn_language(wake_result)
        user_name = self.profile.get_name()
        greeting = self.build_greeting(wake_language, user_name)
        self.speak_with_presence("greeting", "Wake word detected", greeting)

        if not user_name:
            self.capture_user_name(wake_language)
            user_name = self.profile.get_name()

        empty_turns = 0
        for turn in range(MAX_CONVERSATION_TURNS):
            prompt_text = self.listening_prompt(wake_language if self.language_lock is None else self.language_lock, turn, user_name)
            self.display.set_state("listening", "Listening", prompt_text)
            query_result = self.voice.record_query_result()
            query = query_result.transcript.strip()
            if not query:
                empty_turns += 1
                app_logger.warning(f"User query transcript was empty during conversation turn {turn + 1}")
                if empty_turns < 2:
                    retry = "I didn't catch that. Please try again." if wake_language != "hi" else "मैं सुन नहीं पाई। कृपया फिर से बोलिए।"
                    self.display.set_state("listening", "Listening", retry)
                    continue
                self.display.set_state("idle", "Listening timeout", "I will stay quiet for now.")
                return
            empty_turns = 0

            if self.is_stop_command(query):
                farewell = "Okay, shutting down now." if self.get_turn_language(query_result) != "hi" else "ठीक है, मैं अभी रुक रही हूँ।"
                self.speak_with_presence("speaking", "Speaking", farewell)
                self.shutdown()

            app_logger.info(f"Handling user query: {query}")
            self.display.set_state("thinking", "Thinking", "Analyzing your request...")
            try:
                response = self.answer_query(query_result)
            except RuntimeError as exc:
                response = f"Request failed: {exc}"
                app_logger.error(response)
                self.display.set_state("idle", "Request failed", response)
                return

            self.memory.add_exchange(query, response)
            self.speak_with_presence("speaking", "Speaking", self.prepare_spoken_text(response))

        self.display.set_state("idle", "Waiting for wake word", "Say hi, hey, or namaste to begin.")

    def answer_query(self, query_result: SpeechRecognitionResult) -> str:
        query_result = self.resolve_follow_up_query(query_result)
        query = query_result.transcript

        language_switch_response = self.handle_language_switch_request(query_result)
        if language_switch_response is not None:
            return language_switch_response

        local_response = self.handle_local_query(query_result)
        if local_response is not None:
            return local_response

        prompt = self.build_prompt(query_result, include_vision=False)
        if USE_VISION and self.vision_router.is_visual_query(query):
            image_path = self.camera.capture_image()
            scene_hint = self.camera.analyze_scene(image_path)
            app_logger.info(f"Vision scene hint: {scene_hint}")
            prompt = self.build_prompt(query_result, include_vision=True, scene_hint=scene_hint)
            return call_vision_model(str(image_path), prompt)
        return call_text_model(prompt)

    def handle_local_query(self, query_result: SpeechRecognitionResult) -> str | None:
        query = query_result.transcript
        lowered = query.lower().strip()
        turn_language = self.get_turn_language(query_result)

        if self.pending_intent == "reminder":
            self.pending_intent = None
            return self.create_reminder_response(query_result)

        if self.is_time_question(lowered):
            now = datetime.now().astimezone()
            return f"अबhi {now.strftime('%I:%M %p')} हो रहे हैं।" if turn_language == "hi" else f"It is {now.strftime('%I:%M %p')} right now."

        if self.is_date_question(lowered):
            now = datetime.now().astimezone()
            return f"आज {now.strftime('%A, %d %B %Y')} है।" if turn_language == "hi" else f"Today is {now.strftime('%A, %d %B %Y')}."

        if self.is_reminder_request(lowered):
            due_at, message = parse_reminder_request(query, datetime.now().astimezone())
            if due_at and message:
                reminder = self.reminders.add(message, due_at)
                app_logger.info(f"Reminder created: {reminder.message} at {reminder.due_at}")
                return self.format_reminder_confirmation(reminder.message, due_at, turn_language)
            self.pending_intent = "reminder"
            return "Yes, I can set a reminder. Tell me what to remind you about and when." if turn_language != "hi" else "हाँ, मैं reminder सेट कर सकती हूँ। बताइए क्या याद दिलाना है और कब।"

        return None

    def create_reminder_response(self, query_result: SpeechRecognitionResult) -> str:
        due_at, message = parse_reminder_request(query_result.transcript, datetime.now().astimezone())
        turn_language = self.get_turn_language(query_result)
        if not due_at:
            self.pending_intent = "reminder"
            return "I did not catch the reminder time. Please say it like tomorrow at 8 AM, remind me to call mom." if turn_language != "hi" else "मुझे reminder का time साफ़ नहीं मिला। ऐसे बोलिए: कल सुबह 8 बजे माँ को call करने की याद दिलाना।"
        reminder = self.reminders.add(message, due_at)
        app_logger.info(f"Reminder created: {reminder.message} at {reminder.due_at}")
        return self.format_reminder_confirmation(reminder.message, due_at, turn_language)

    def format_reminder_confirmation(self, message: str, due_at: datetime, language: str) -> str:
        if language == "hi":
            return f"ठीक है। मैं आपको {due_at.strftime('%A, %d %B')} को {due_at.strftime('%I:%M %p')} पर {message} की याद दिलाऊँगी।"
        return f"Done. I will remind you to {message} on {due_at.strftime('%A, %d %B')} at {due_at.strftime('%I:%M %p')}."

    def check_due_reminders(self) -> None:
        now = datetime.now().astimezone()
        for reminder in self.reminders.get_due(now):
            announcement = f"Reminder. It is time to {reminder.message}."
            app_logger.info(f"Reminder due: {reminder.message}")
            self.speak_with_presence("speaking", "Reminder", announcement)
            self.reminders.mark_spoken(reminder.id)

    def build_prompt(self, query_result: SpeechRecognitionResult, include_vision: bool, scene_hint: str = "") -> str:
        query = query_result.transcript
        speech_language = self.get_turn_language(query_result)
        user_name = self.profile.get_name() or "unknown"
        context = self.memory.get_context_block(max_chars=420)
        prompt_lines = [
            "You are PraSush, a personal ambient AI assistant with voice, memory, and optional vision.",
            "PraSush is your name only.",
            self.build_output_language_instruction(speech_language),
            "Reply directly and naturally. Do not switch languages unless the current user turn asks for it.",
            "Avoid generic filler and availability lines. Answer the question itself.",
            f"Known user name: {user_name}",
            self.build_runtime_context(),
            f"Recent context: {context}",
            f"Current turn language: {speech_language}",
            f"Vision enabled: {'yes' if include_vision else 'no'}",
            "If vision is enabled, the latest camera image represents what you can currently see.",
            "Do not claim biometric identity recognition.",
            f"User query: {query}",
            "Assistant:",
        ]
        if scene_hint:
            prompt_lines.insert(-2, f"Camera analysis hint: {scene_hint}")
        return "\n".join(prompt_lines)

    def build_runtime_context(self) -> str:
        now = datetime.now().astimezone()
        return (
            f"Current runtime context: Date: {now.strftime('%A, %d %B %Y')}. "
            f"Time: {now.strftime('%I:%M %p')}. "
            f"Timezone: {now.tzname() or LOCAL_TIMEZONE}. "
            f"Workspace location: {BASE_DIR}."
        )

    def build_output_language_instruction(self, speech_language: str) -> str:
        if speech_language == "hi":
            return "The current user turn is Hindi. Reply fully in Hindi. Do not answer in English."
        if speech_language == "hinglish":
            return "The current user turn is Hinglish. Reply in natural Hinglish using Roman script. Do not switch to full English."
        return "The current user turn is English. Reply in English."

    def handle_language_switch_request(self, query_result: SpeechRecognitionResult) -> str | None:
        lowered = query_result.transcript.lower()
        if any(marker in lowered for marker in ("speak hindi", "speak in hindi", "hindi mein bolo", "hindi me bolo", "hindi mein baat karo", "हिंदी में बोलो")):
            self.language_lock = "hi"
            return "जी हाँ, अब से मैं आपसे हिंदी में बात करूँगी।"
        if any(marker in lowered for marker in ("speak english", "talk in english", "english mein bolo", "english me bolo")):
            self.language_lock = "en"
            return "Sure, I will speak in English now."
        return None

    def resolve_follow_up_query(self, query_result: SpeechRecognitionResult) -> SpeechRecognitionResult:
        query = query_result.transcript.strip()
        if not query or not self.is_follow_up_query(query):
            return query_result
        previous_topic = self.get_recent_topic()
        if not previous_topic:
            return query_result
        if self.get_turn_language(query_result) == "hi":
            expanded = f"पिछले विषय '{previous_topic}' के बारे में और विस्तार से बताओ।"
            return SpeechRecognitionResult(transcript=expanded, detected_language="hi", mode=query_result.mode)
        return SpeechRecognitionResult(transcript=f"Tell me more about {previous_topic}.", detected_language="en", mode=query_result.mode)

    def capture_user_name(self, language: str) -> None:
        ask_text = ASK_NAME_MESSAGE_HI if language == "hi" else ASK_NAME_MESSAGE
        listen_text = "अपना नाम बताइए।" if language == "hi" else "Tell me your name."
        self.speak_with_presence("greeting", "Getting to know you", ask_text)
        self.display.set_state("listening", "Listening for your name", listen_text)
        spoken_name_result = self.voice.record_query_result()
        parsed_name = self.extract_name(spoken_name_result.transcript)
        if not parsed_name:
            fallback = "जब मुझे आपका नाम साफ़ सुनाई देगा, मैं उसे याद रखूँगी।" if language == "hi" else "I will remember your name once I hear it clearly."
            self.speak_with_presence("speaking", "Speaking", fallback)
            return
        self.profile.set_name(parsed_name)
        confirmation = f"आपसे मिलकर अच्छा लगा, {parsed_name}। मैं आपका नाम याद रखूँगी।" if language == "hi" else f"Nice to meet you, {parsed_name}. I will remember your name."
        self.speak_with_presence("speaking", "Speaking", confirmation)

    def build_greeting(self, language: str, user_name: str | None) -> str:
        if language == "hi":
            return f"नमस्ते {user_name}, मैं प्रसुष हूँ। मैं आपके साथ हूँ।" if user_name else GREETING_MESSAGE_HI
        return f"Hello {user_name}, I am PraSush. I am here with you." if user_name else GREETING_MESSAGE

    def listening_prompt(self, language: str, turn: int, user_name: str | None) -> str:
        if language == "hi":
            if turn == 0 and user_name:
                return f"आप क्या जानना चाहेंगे, {user_name}?"
            if turn == 0:
                return "आप क्या जानना चाहेंगे?"
            return FOLLOW_UP_PROMPT_HI
        if turn == 0 and user_name:
            return f"What would you like to know, {user_name}?"
        if turn == 0:
            return "What would you like to know?"
        return FOLLOW_UP_PROMPT

    def get_turn_language(self, query_result: SpeechRecognitionResult) -> str:
        if self.language_lock in {"hi", "en"}:
            return self.language_lock
        return self.normalize_speech_language(query_result.transcript)

    def normalize_speech_language(self, query: str) -> str:
        lowered = query.lower()
        if any("\u0900" <= char <= "\u097f" for char in query):
            return "hi"
        if any(marker in lowered for marker in ("namaste", "namaskar", "kya", "aap", "hain", "hai", "batao", "samay", "aur batao", "yaad dilao", "kaise")):
            return "hinglish"
        return "en"

    def extract_name(self, spoken_text: str) -> str:
        cleaned = spoken_text.strip()
        patterns = [
            r"\bmy name is ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bi am ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bcall me ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bmera naam hai ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return self.normalize_name(match.group(1))
        if len(cleaned.split()) <= 3:
            return self.normalize_name(cleaned)
        return ""

    def normalize_name(self, value: str) -> str:
        if any("\u0900" <= char <= "\u097f" for char in value):
            return " ".join(value.split()[:3])
        letters_only = re.sub(r"[^A-Za-z'\- ]", "", value).strip()
        return " ".join(part.capitalize() for part in letters_only.split()[:3])

    def is_stop_command(self, spoken_text: str) -> bool:
        lowered = spoken_text.lower()
        normalized = " ".join(re.sub(r"[^a-z ]", " ", lowered).split())
        return any(phrase in normalized for phrase in STOP_PHRASES) or any(phrase in lowered for phrase in HINDI_STOP_PHRASES)

    def prepare_spoken_text(self, text: str) -> str:
        cleaned = text.replace("**", "").replace("*", "")
        cleaned = re.sub(r"\bUser query:.*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\bAssistant:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def is_reminder_request(self, lowered: str) -> bool:
        return any(pattern in lowered for pattern in ("remind me", "set a reminder", "reminder", "alarm", "yaad dilana", "yaad dila", "याद दिलाना", "याद दिला"))

    def is_time_question(self, lowered: str) -> bool:
        return any(pattern in lowered for pattern in ("what time", "current time", "time is it", "tell me the time", "kitna time", "kya time", "samay", "कितना समय", "क्या समय", "समय"))

    def is_date_question(self, lowered: str) -> bool:
        return any(pattern in lowered for pattern in ("what is the date", "today's date", "what day is it", "tell me the date", "aaj ki date", "tareekh", "तारीख", "आज"))

    def is_follow_up_query(self, query: str) -> bool:
        normalized = " ".join(re.sub(r"[^a-z\u0900-\u097f ]", " ", query.lower()).split())
        return normalized in FOLLOW_UP_MARKERS

    def get_recent_topic(self) -> str:
        for exchange in reversed(self.memory.history):
            candidate = exchange.user.strip()
            if candidate and not self.is_follow_up_query(candidate):
                return candidate
        return ""

    def is_wake_match(self, spoken_text: str) -> bool:
        normalized = " ".join(re.sub(r"[^a-z\u0900-\u097f ]", " ", spoken_text.lower()).split())
        if WAKE_WORD in normalized or normalized in {"hi", "hello", "hey", "namaste", "namaskar"}:
            return True
        if len(normalized.split()) > 3:
            return False
        return any(variant in normalized for variant in WAKE_VARIANTS)

    def speak_with_presence(self, state: str, status_text: str, message: str) -> None:
        self.display.set_state(state, status_text, message)
        self.voice.start_speaking(message)
        while self.voice.is_speaking():
            self.display.pump_events()
            self.display.render()
            time.sleep(0.03)
        self.voice.wait_until_done()
        self.display.render()

    def shutdown(self) -> None:
        app_logger.info("PraSush shutting down")
        self.camera.close()
        self.display.close()
        sys.exit(0)


if __name__ == "__main__":
    PraSushApp().run()

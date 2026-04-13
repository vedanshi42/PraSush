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
ASK_NAME_MESSAGE = "Before we begin, what should I call you?"
STOP_PHRASES = {"stop", "shut down", "shutdown", "close", "exit", "bye"}
HINDI_STOP_PHRASES = {
    "band",
    "band karo",
    "band ho jao",
    "band hojao",
    "band ho jaiye",
    "band hojaiye",
    "ruk",
    "ruko",
    "ruk jaiye",
    "ruk jao",
    "ruk jaiyega",
    "bas",
    "\u092c\u0938",
    "\u092c\u0902\u0926",
    "\u092c\u0902\u0926 \u0915\u0930\u094b",
    "\u092c\u0902\u0926 \u0939\u094b \u091c\u093e\u0913",
    "\u092c\u0902\u0926 \u0939\u094b \u091c\u093e\u0907\u090f",
    "\u0930\u0941\u0915\u094b",
    "\u0930\u0941\u0915 \u091c\u093e\u0907\u090f",
    "\u0930\u0941\u0915 \u091c\u093e\u0913",
}
MAX_CONVERSATION_TURNS = 6
FOLLOW_UP_PROMPT = "I'm listening. Ask another question, or say stop."
FOLLOW_UP_MARKERS = (
    "aur",
    "aur batao",
    "aur bataye",
    "aur batayiye",
    "aur jankari",
    "to dijiye",
    "to diji hai",
    "toh dijiye",
    "thoda aur",
    "continue",
    "go on",
    "tell me more",
    "more details",
    "\u0914\u0930",
    "\u0914\u0930 \u092c\u0924\u093e\u0913",
    "\u0914\u0930 \u092c\u0924\u093e\u0907\u090f",
    "\u0914\u0930 \u091c\u093e\u0928\u0915\u093e\u0930\u0940",
    "\u0924\u094b \u0926\u0940\u091c\u093f\u090f",
    "\u0925\u094b\u0921\u093c\u093e \u0914\u0930",
)


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
        self.response_language_preference: str | None = None

    def run(self) -> None:
        self.display.set_state("idle", "Waiting for wake word", "Say 'Hey PraSush' to begin.")
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
                    time.sleep(0.8)
                self.display.render()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def handle_interaction(self, wake_result: SpeechRecognitionResult) -> None:
        user_name = self.profile.get_name()
        wake_language = self.normalize_speech_language(wake_result.detected_language, wake_result.transcript)
        if wake_language == "hi" or "namaste" in wake_result.transcript.lower() or "namaskar" in wake_result.transcript.lower():
            greeting = (
                f"\u0928\u092e\u0938\u094d\u0924\u0947 {user_name}, \u092e\u0948\u0902 \u092a\u094d\u0930\u0938\u0941\u0937 \u0939\u0942\u0901\u0964 \u092e\u0948\u0902 \u0906\u092a\u0915\u0947 \u0938\u093e\u0925 \u0939\u0942\u0901\u0964"
                if user_name
                else "\u0928\u092e\u0938\u094d\u0924\u0947, \u092e\u0948\u0902 \u092a\u094d\u0930\u0938\u0941\u0937 \u0939\u0942\u0901\u0964 \u092e\u0948\u0902 \u0906\u092a\u0915\u0947 \u0938\u093e\u0925 \u0939\u0942\u0901\u0964"
            )
        else:
            greeting = f"Hello {user_name}, I am PraSush. I am here with you." if user_name else GREETING_MESSAGE
        self.speak_with_presence("greeting", "Wake word detected", greeting)

        if not user_name:
            self.capture_user_name()
            user_name = self.profile.get_name()

        empty_turns = 0
        for turn in range(MAX_CONVERSATION_TURNS):
            prompt_text = (
                (
                    f"\u0906\u092a \u0915\u094d\u092f\u093e \u091c\u093e\u0928\u0928\u093e \u091a\u093e\u0939\u0947\u0902\u0917\u0947, {user_name}?"
                    if turn == 0 and user_name
                    else "\u092e\u0948\u0902 \u0938\u0941\u0928 \u0930\u0939\u0940 \u0939\u0942\u0901\u0964 \u0905\u0917\u0932\u093e \u0938\u0935\u093e\u0932 \u092a\u0942\u091b\u093f\u090f \u092f\u093e \u0930\u0941\u0915\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f stop \u0915\u0939\u093f\u090f\u0964"
                    if turn > 0
                    else "\u0906\u092a \u0915\u094d\u092f\u093e \u091c\u093e\u0928\u0928\u093e \u091a\u093e\u0939\u0947\u0902\u0917\u0947?"
                )
                if self.response_language_preference == "hi"
                else (
                    f"What would you like to know, {user_name}?"
                    if turn == 0 and user_name
                    else FOLLOW_UP_PROMPT
                    if turn > 0
                    else "What would you like to know?"
                )
            )
            self.display.set_state("listening", "Listening", prompt_text)
            query_result = self.voice.record_query_result()
            query = query_result.transcript
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
                farewell = (
                    "\u0920\u0940\u0915 \u0939\u0948, \u092e\u0948\u0902 \u0905\u092d\u0940 \u0930\u0941\u0915 \u0930\u0939\u0940 \u0939\u0942\u0901\u0964"
                    if self.response_language_preference == "hi" or self.prefers_hindi(query)
                    else "Okay, shutting down now."
                )
                self.speak_with_presence("speaking", "Speaking", farewell)
                self.shutdown()

            app_logger.info(f"Handling user query: {query}")
            self.display.set_state("thinking", "Thinking", "Analyzing your request...")
            try:
                response = self.answer_query(query_result)
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

    def answer_query(self, query_result: SpeechRecognitionResult) -> str:
        query_result = self.resolve_follow_up_query(query_result)
        query = query_result.transcript
        language_switch_response = self.handle_language_switch_request(query_result)
        if language_switch_response is not None:
            return language_switch_response
        local_response = self.handle_local_query(query)
        if local_response is not None:
            return local_response

        prompt = self.build_prompt(query_result, include_vision=False)
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
            prompt = self.build_prompt(query_result, include_vision=True, scene_hint=scene_hint)
            return call_vision_model(str(image_path), prompt)
        return call_text_model(prompt)

    def resolve_follow_up_query(self, query_result: SpeechRecognitionResult) -> SpeechRecognitionResult:
        query = query_result.transcript.strip()
        if not query or not self.is_follow_up_query(query):
            return query_result

        previous_topic = self.get_recent_topic()
        if not previous_topic:
            return query_result

        if self.prefers_hindi(query) or self.normalize_speech_language(query_result.detected_language, query) in {"hi", "hinglish"}:
            expanded = (
                f"\u092a\u093f\u091b\u0932\u0947 \u0935\u093f\u0937\u092f \u0915\u094b \u091c\u093e\u0930\u0940 \u0930\u0916\u0924\u0947 \u0939\u0941\u090f "
                f"'{previous_topic}' \u0915\u0947 \u092c\u093e\u0930\u0947 \u092e\u0947\u0902 \u0914\u0930 \u0935\u093f\u0938\u094d\u0924\u093e\u0930 \u0938\u0947 \u092c\u0924\u093e\u090f\u0901\u0964"
            )
            detected_language = "hi"
        else:
            expanded = f"Continue the previous topic and tell me more about: {previous_topic}."
            detected_language = "en"

        app_logger.info(f"Expanded short follow-up query '{query}' to '{expanded}'")
        return SpeechRecognitionResult(transcript=expanded, detected_language=detected_language, mode=query_result.mode)

    def handle_local_query(self, query: str) -> str | None:
        lowered = query.lower().strip()
        if self.pending_intent == "reminder":
            self.pending_intent = None
            return self.create_reminder_response(query)

        if self.is_time_question(lowered):
            now = datetime.now().astimezone()
            if self.prefers_hindi(query):
                return f"\u0905\u092d\u0940 {now.strftime('%I:%M %p')} \u0939\u094b \u0930\u0939\u0947 \u0939\u0948\u0902\u0964"
            return f"It is {now.strftime('%I:%M %p')} for us right now."

        if self.is_date_question(lowered):
            now = datetime.now().astimezone()
            if self.prefers_hindi(query):
                return f"\u0906\u091c {now.strftime('%A, %d %B %Y')} \u0939\u0948\u0964"
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

    def build_prompt(self, query_result: SpeechRecognitionResult, include_vision: bool, scene_hint: str = "") -> str:
        context = self.memory.get_context_block()
        user_name = self.profile.get_name() or "unknown"
        runtime_context = self.build_runtime_context()
        query = query_result.transcript
        speech_language = self.normalize_speech_language(query_result.detected_language, query)
        if self.response_language_preference in {"hi", "hinglish", "en"}:
            speech_language = self.response_language_preference
        output_language_instruction = self.build_output_language_instruction(speech_language)
        prompt_lines = [
            "You are PraSush, a personal ambient AI assistant with voice, memory, and optional vision.",
            "PraSush is your name only. Do not reinterpret it as a blog, brand, recipe, company, acronym, or anything else.",
            "Be concise, helpful, warm, and conversational. Refer to yourself as PraSush when asked your name.",
            "You support English, Hindi, and Hinglish. Reply in the same language or language mix the user uses, unless they ask for a different language.",
            output_language_instruction,
            "For Hinglish, keep the tone natural for Indian users. Avoid sounding like a literal translation.",
            "Answer in natural spoken sentences. Avoid markdown, bullet lists, and repeated 'User query' / 'Assistant' labels in the answer.",
            "Carry conversation naturally across turns. If the user asks a follow-up like 'tell me more', 'aur batao', or asks about the same topic again, continue the previous topic instead of resetting.",
            "If the user's transcript sounds partial or slightly awkward, infer the most likely intended meaning from recent context and answer helpfully.",
            "Do not reply with generic lines about being available for conversation unless the user explicitly asks whether you are available or listening.",
            "When the user asks an informational question, answer the question directly instead of reflecting it back.",
            f"Known user name: {user_name}",
            runtime_context,
            f"Previous context: {context}",
            f"Detected speech language: {speech_language}",
            f"Vision enabled for this turn: {'yes' if include_vision else 'no'}",
            "If vision is enabled, assume the latest camera image represents what you can currently see.",
            "If vision is enabled and the user's question is in Hindi or Hinglish, first understand the visual question internally and then answer finally in the requested Hindi or Hinglish style.",
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

    def normalize_speech_language(self, detected_language: str, query: str) -> str:
        lowered = query.lower()
        if any("\u0900" <= char <= "\u097f" for char in query):
            return "hi"
        if any(marker in lowered for marker in ("hindi mein", "hindi me", "jawab do", "devnagari", "devanagari")):
            return "hi"
        if any(marker in lowered for marker in ("speak hindi", "speak in hindi", "talk in hindi", "please speak hindi")):
            return "hi"
        if detected_language == "hi":
            if any(marker in lowered for marker in ("kya", "aap", "hain", "hai", "batao", "samay", "kaise")):
                return "hinglish"
            return "hi"
        if any(marker in lowered for marker in ("kya", "aap", "hain", "hai", "batao", "samay", "kaise")):
            return "hinglish"
        return "en"

    def handle_language_switch_request(self, query_result: SpeechRecognitionResult) -> str | None:
        query = query_result.transcript
        lowered = query.lower()
        hindi_switch_markers = (
            "speak hindi",
            "speak in hindi",
            "talk in hindi",
            "please speak hindi",
            "hindi mein bolo",
            "hindi me bolo",
            "hindi mein baat karo",
            "hindi me baat karo",
            "\u0939\u093f\u0902\u0926\u0940 \u092e\u0947\u0902 \u092c\u094b\u0932\u094b",
            "\u0939\u093f\u0902\u0926\u0940 \u092e\u0947\u0902 \u092c\u093e\u0924 \u0915\u0930\u094b",
        )
        english_switch_markers = (
            "speak english",
            "talk in english",
            "english mein bolo",
            "english me bolo",
        )

        if any(marker in lowered for marker in hindi_switch_markers):
            self.response_language_preference = "hi"
            return "\u091c\u0940 \u0939\u093e\u0901, \u0905\u092c \u0938\u0947 \u092e\u0948\u0902 \u0906\u092a\u0938\u0947 \u0939\u093f\u0902\u0926\u0940 \u092e\u0947\u0902 \u092c\u093e\u0924 \u0915\u0930\u0942\u0901\u0917\u0940\u0964 \u0906\u092a \u0905\u092a\u0928\u093e \u0938\u0935\u093e\u0932 \u092a\u0942\u091b\u093f\u090f\u0964"
        if any(marker in lowered for marker in english_switch_markers):
            self.response_language_preference = "en"
            return "Sure, I will speak in English now. Please ask your question."
        return None

    def build_output_language_instruction(self, speech_language: str) -> str:
        if speech_language == "hi":
            return (
                "The user's speech language is Hindi. Reply fully in natural Hindi using Devanagari script only. "
                "Do not answer in English. Do not say that you can speak Hindi; directly answer the question in Hindi. "
                "Do not reply with placeholder lines such as saying you can provide information; provide the information itself."
            )
        if speech_language == "hinglish":
            return (
                "The user's speech language is Hinglish. Reply in natural Hinglish using Roman script. "
                "Do not switch to fully English unless the user asks for English. "
                "Do not reply with placeholder lines; answer directly."
            )
        return "The user's speech language is English. Reply in English."

    def capture_user_name(self) -> None:
        self.speak_with_presence("greeting", "Getting to know you", ASK_NAME_MESSAGE)
        self.display.set_state("listening", "Listening for your name", "Tell me your name.")
        spoken_name_result = self.voice.record_query_result()
        parsed_name = self.extract_name(spoken_name_result.transcript)
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
            r"\bmy name is ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bi am ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bi'm ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bcall me ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bmera naam hai ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
            r"\bmain hoon ([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f'\- ]{0,40})",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return self.normalize_name(match.group(1))
        if len(cleaned.split()) <= 3:
            return self.normalize_name(cleaned)
        return ""

    def normalize_name(self, value: str) -> str:
        value = value.strip()
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
        patterns = (
            "remind me",
            "set a reminder",
            "create a reminder",
            "reminder",
            "alarm",
            "yaad dilana",
            "yaad dila",
            "\u092f\u093e\u0926 \u0926\u093f\u0932\u093e\u0928\u093e",
            "\u092f\u093e\u0926 \u0926\u093f\u0932\u093e",
        )
        return any(pattern in lowered for pattern in patterns)

    def is_time_question(self, lowered: str) -> bool:
        explicit_phrases = (
            "what time",
            "current time",
            "time is it",
            "tell me the time",
            "kitna time",
            "kya time",
            "kitna samay",
            "\u0915\u093f\u0924\u0928\u093e \u0938\u092e\u092f",
            "\u0915\u094d\u092f\u093e \u0938\u092e\u092f",
        )
        if any(pattern in lowered for pattern in explicit_phrases):
            return True
        return bool(re.search(r"\b(samay|time)\b.*\b(kya|kitna|batao|bataye)\b", lowered))

    def is_date_question(self, lowered: str) -> bool:
        explicit_phrases = (
            "what is the date",
            "today's date",
            "what day is it",
            "tell me the date",
            "aaj ki date",
            "aaj ka din",
            "aaj tareekh",
            "\u0906\u091c \u0915\u0940 \u0924\u093e\u0930\u0940\u0916",
            "\u0906\u091c \u0915\u093e \u0926\u093f\u0928",
        )
        if any(pattern in lowered for pattern in explicit_phrases):
            return True
        return bool(re.search(r"\b(date|day|tareekh|tarikh)\b.*\b(kya|kaun|batao|bataye)\b", lowered))

    def prefers_hindi(self, text: str) -> bool:
        lowered = text.lower()
        hindi_markers = (
            "hindi",
            "hinglish",
            "kitna",
            "kya",
            "samay",
            "aaj",
            "batao",
            "yaad",
            "kaise",
            "hai",
        )
        return any("\u0900" <= char <= "\u097f" for char in text) or any(marker in lowered for marker in hindi_markers)

    def is_follow_up_query(self, query: str) -> bool:
        lowered = query.lower().strip()
        normalized = " ".join(re.sub(r"[^a-z\u0900-\u097f ]", " ", lowered).split())
        if normalized in FOLLOW_UP_MARKERS:
            return True
        if len(normalized.split()) <= 4 and any(marker in normalized for marker in FOLLOW_UP_MARKERS):
            return True
        return False

    def get_recent_topic(self) -> str:
        for exchange in reversed(self.memory.history):
            candidate = exchange.user.strip()
            if candidate and not self.is_follow_up_query(candidate):
                return candidate
        return ""

    def is_wake_match(self, spoken_text: str) -> bool:
        lowered = spoken_text.lower().strip()
        normalized = re.sub(r"[^a-z\u0900-\u097f ]", " ", lowered)
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

import time
import sys
from datetime import datetime
from voice.recognizer import VoiceAssistant
from llm.client import OllamaClient
from vision.camera import CameraInput
from ui.display import DisplayManager
from memory.store import MemoryStore
from logger import app_logger

WAKE_KEYWORDS = ["hi", "hey prasush", "hey pra sush", "hey prashush"]
VISUAL_KEYWORDS = [
    "see",
    "look",
    "camera",
    "image",
    "describe",
    "photo",
    "picture",
    "what do you see",
    "what is in",
    "what's in",
    "what am i seeing",
    "vision",
]


class PraSushApp:
    def __init__(self):
        self.display = DisplayManager()
        self.display.hide()
        self.memory = MemoryStore()
        self.voice = VoiceAssistant()
        self.llm = OllamaClient()
        self.camera = CameraInput()
        self.active = False

    def run(self):
        self.display.hide()
        self.display.render()
        try:
            while True:
                self.display.pump_events()
                self.display.render()
                if self.active:
                    self.active = self.handle_interaction()
                else:
                    wake_text = self.voice.listen_for_wakeword()
                    if wake_text and self.contains_wake_word(wake_text):
                        app_logger.info(f"Wake word detected: {wake_text}")
                        self.active = True
                        self.display.set_environment_summary("Wake word heard. Ready for your question.")
                        self.display.set_subtitle("Please ask your question.")
                        self.display.render()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def contains_wake_word(self, text: str) -> bool:
        lowered = text.lower().strip()
        if not lowered:
            return False

        # Exact phrase match
        if any(keyword in lowered for keyword in WAKE_KEYWORDS):
            return True

        # Fuzzy match for minor transcription errors
        from difflib import SequenceMatcher

        threshold = 0.66
        for keyword in WAKE_KEYWORDS:
            ratio = SequenceMatcher(None, lowered, keyword).ratio()
            if ratio >= threshold:
                app_logger.info(f"Fuzzy wake word match: {lowered} ~ {keyword} ({ratio:.2f})")
                return True
        return False

    def is_affirmative(self, text: str) -> bool:
        lower = text.lower().strip()
        if not lower:
            return False
        affirm = ["yes", "sure", "yep", "yeah", "ok", "okay", "continue", "go on"]
        deny = ["no", "nope", "stop", "bye", "later"]
        if any(word in lower for word in affirm):
            return True
        if any(word in lower for word in deny):
            return False
        # If not clear, treat as non-affirmative
        return False

    def handle_interaction(self):
        self.display.set_active()
        self.display.set_environment_summary("Ambient awareness is active. Observing room motion, light, and sound.")
        self.display.set_subtitle("I heard you. Please speak your question.")
        self.display.render()
        self.voice.speak("Yes. I am listening.")
        time.sleep(1)

        query = self.voice.record_query()
        if not query:
            self.display.set_subtitle("I could not hear that. Say Hey PraSush again.")
            self.display.render()
            self.voice.speak("I did not catch that. Please say Hey PraSush again.")
            time.sleep(1)
            return False

        visual_prompt = None
        if self.is_visual_request(query):
            self.display.set_subtitle("Checking the camera for you...")
            self.display.render()
            self.voice.speak("I am checking the camera for you.")
            time.sleep(1)
            try:
                frame, image_path = self.camera.capture_image()
                visual_prompt = self.camera.describe_frame(frame)
                self.display.set_environment_summary(visual_prompt)
                self.display.set_subtitle("Camera summary ready.")
                self.display.render()
            except RuntimeError:
                visual_prompt = "I could not access the camera."

        prompt = self.build_prompt(query, visual_prompt)
        app_logger.llm_request(prompt)

        self.display.set_subtitle("Thinking...")
        self.display.render()

        response = self.llm.ask(prompt)
        if not response:
            response = "I am sorry, I could not get a response right now."
            app_logger.error(f"LLM returned empty response for query: {query}")

        self.memory.add_interaction("user", query)
        self.memory.add_interaction("assistant", response)

        self.display.set_subtitle(response)
        self.display.render()

        app_logger.info("Speaking response asynchronously")
        self.voice.speak(response)

        # Allow speech to begin and continue
        time.sleep(2)

        # Follow-up question for conversation flow
        self.display.set_subtitle("Would you like to ask another question? Say yes or no.")
        self.display.render()
        self.voice.speak("Would you like to ask another question? Say yes or no.")
        time.sleep(1)

        follow_up = self.voice.record_query()
        if self.is_affirmative(follow_up):
            self.display.set_subtitle("Great! Ask your next question.")
            self.display.render()
            return True

        self.display.set_subtitle("Okay, I will wait for the wake word.")
        self.display.render()
        self.voice.speak("Okay, I will wait for the wake word.")
        time.sleep(1)
        return False

    def is_visual_request(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in VISUAL_KEYWORDS)

    def build_prompt(self, user_query: str, visual_summary: str | None) -> str:
        context = self.memory.get_context()
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        
        prompt_lines = [
            "You are PraSush, an ambient AI assistant. You are friendly, conversational, intelligent, and adaptable.",
            "Speak naturally and concisely. Be conversational and follow up with relevant questions when appropriate.",
            "When asked about time or date, provide the current information: " + f"Current time: {time_str}, Date: {date_str}",
            "Maintain context from recent interactions for smooth, coherent conversations.",
            "If you don't know something, say so honestly but try to be helpful.",
        ]
        if context:
            prompt_lines.append("")
            prompt_lines.append("Recent conversation history (for context):")
            prompt_lines.append(context)
        if visual_summary:
            prompt_lines.append("")
            prompt_lines.append("What I see right now (camera):")
            prompt_lines.append(visual_summary)
        prompt_lines.append("")
        prompt_lines.append(f"User: {user_query}")
        prompt_lines.append("")
        prompt_lines.append("Assistant:")
        return "\n".join(prompt_lines)

    def shutdown(self):
        app_logger.info("Shutting down PraSush")
        self.camera.close()
        self.display.close()
        app_logger.info("PraSush shutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    app = PraSushApp()
    app.run()

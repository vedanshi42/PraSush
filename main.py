import time
import sys
from voice.recognizer import VoiceAssistant
from llm.client import OllamaClient
from vision.camera import CameraInput
from ui.display import DisplayManager
from memory.store import MemoryStore

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
        self.memory = MemoryStore()
        self.voice = VoiceAssistant()
        self.llm = OllamaClient()
        self.camera = CameraInput()
        self.active = False

    def run(self):
        self.display.set_idle()
        self.display.render()
        try:
            while True:
                self.display.pump_events()
                if self.active:
                    self.handle_interaction()
                else:
                    wake_text = self.voice.listen_for_wakeword()
                    if wake_text and self.contains_wake_word(wake_text):
                        self.active = True
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def contains_wake_word(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in WAKE_KEYWORDS)

    def handle_interaction(self):
        self.active = False
        self.display.set_active()
        self.display.set_subtitle("I heard you. Please speak your question.")
        self.display.render()
        self.voice.speak("Yes. I am listening.")

        query = self.voice.record_query()
        if not query:
            self.display.set_subtitle("I could not hear that. Say Hey PraSush again.")
            self.voice.speak("I did not catch that. Please say Hey PraSush again.")
            return

        visual_prompt = None
        if self.is_visual_request(query):
            self.voice.speak("I am checking the camera for you.")
            try:
                frame, image_path = self.camera.capture_image()
                visual_prompt = self.camera.describe_frame(frame)
                self.display.set_subtitle("Captured an image for your question.")
                self.display.render()
            except RuntimeError:
                visual_prompt = "I could not access the camera."

        prompt = self.build_prompt(query, visual_prompt)
        self.display.set_subtitle("Thinking...")
        self.display.render()

        response = self.llm.ask(prompt)
        if not response:
            response = "I am sorry, I could not get a response right now."

        self.memory.add_interaction("user", query)
        self.memory.add_interaction("assistant", response)

        self.display.set_subtitle(response)
        self.display.render()
        self.voice.speak(response)
        self.display.set_idle()
        self.display.render()

    def is_visual_request(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in VISUAL_KEYWORDS)

    def build_prompt(self, user_query: str, visual_summary: str | None) -> str:
        context = self.memory.get_context()
        prompt_lines = [
            "You are PraSush, an ambient projector assistant that stays quiet until the wake word is spoken.",
            "Answer clearly and include any memory context from recent interactions.",
        ]
        if context:
            prompt_lines.append("Recent memory:")
            prompt_lines.append(context)
        if visual_summary:
            prompt_lines.append("The user asked a visual question. Here is the camera summary:")
            prompt_lines.append(visual_summary)
        prompt_lines.append(f"User: {user_query}")
        prompt_lines.append("Assistant:")
        return "\n".join(prompt_lines)

    def shutdown(self):
        self.camera.close()
        self.display.close()
        sys.exit(0)


if __name__ == "__main__":
    app = PraSushApp()
    app.run()

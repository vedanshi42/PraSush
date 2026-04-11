from pathlib import Path

USE_VISION = True
AUTO_UNLOAD_VISION = True
MAX_MEMORY_CONTEXT = 5
AVATAR_IMAGE_PATH = "avatar.png"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
LOCAL_TIMEZONE = "Asia/Calcutta"
TTS_RATE = 1
TTS_PITCH = "+18%"
TTS_VOICE_MAC = "Samantha"
STT_LANGUAGE = None  # None lets Whisper auto-detect English, Hindi, and Hinglish.
SUPPORTED_SPOKEN_LANGUAGES = ["English", "Hindi", "Hinglish"]

OLLAMA_ENDPOINT = "http://localhost:11434/api"
LLM_PROVIDER = "cometapi"
OLLAMA_TEXT_MODEL = "phi3"
VISION_MODEL = "llava"
GOOGLE_MODEL = "gemini-2.5-flash"
GOOGLE_API_KEY_ENV = "GEMINI_API_KEY"
GOOGLE_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
COMET_API_KEY_ENV = "COMET_API_KEY"
COMET_API_ENDPOINT = "https://api.cometapi.com/v1"
COMET_MODEL = "gemini-2.5-flash"

VISION_KEYWORDS = ["see", "look", "what is this", "describe", "camera"]
WAKE_WORD = "hey prasush"
WAKE_VARIANTS = [
    "hi",
    "hello",
    "hey",
    "namaste",
    "namaskar",
    "hey pra",
    "hi pra",
    "pra suno",
    "prasush suno",
    "hey prasu",
    "hey prasush",
    "hey pra sush",
    "hey prashush",
    "pra",
    "prasush",
]
PROJECT_NAME = "PraSush"

BASE_DIR = Path(__file__).resolve().parent
AVATAR_PATH = BASE_DIR / AVATAR_IMAGE_PATH
MEMORY_PATH = BASE_DIR / "memory" / "history.json"
PROFILE_PATH = BASE_DIR / "memory" / "profile.json"
REMINDERS_PATH = BASE_DIR / "memory" / "reminders.json"
SCENE_IMAGE_PATH = BASE_DIR / "scene.jpg"

import os
from pathlib import Path

USE_VISION = True
MAX_MEMORY_CONTEXT = 3
AVATAR_IMAGE_PATH = "avatar.png"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
SUBTITLE_FONT_NAME = os.getenv("SUBTITLE_FONT_NAME", "Nirmala UI")
STATUS_FONT_NAME = os.getenv("STATUS_FONT_NAME", "Segoe UI")
LOCAL_TIMEZONE = "Asia/Calcutta"
TTS_RATE = 1
TTS_PITCH = "+18%"
TTS_VOICE_MAC = "Samantha"
TTS_ENABLE_GTTS = True
SUPPORTED_SPOKEN_LANGUAGES = ["English", "Hindi", "Hinglish"]
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "small")
WAKEWORD_MAX_RECORD_SECONDS = 2.5
QUERY_MAX_RECORD_SECONDS = 8.0
END_OF_SPEECH_SILENCE_SECONDS = 1.8
MIN_SPEECH_SECONDS = 0.35
SPEECH_START_THRESHOLD = 0.010
SPEECH_SILENCE_THRESHOLD = 0.006
STT_INITIAL_PROMPT = (
    "The speaker may use English, Hindi, or Hinglish. "
    "Important words include PraSush, Namaste, kya, samay, aur batao, "
    "Hindi mein jawab do, speak in English."
)

NVIDIA_API_KEY_ENV = "NVIDIA_API_KEY"
NVIDIA_API_ENDPOINT = "https://integrate.api.nvidia.com/v1"
NVIDIA_TEXT_MODEL = os.getenv("NVIDIA_TEXT_MODEL", "nvidia/llama-3.1-nemotron-ultra-253b-v1")
NVIDIA_VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "microsoft/phi-4-multimodal-instruct")

VISION_KEYWORDS = [
    "see",
    "look",
    "what is this",
    "describe",
    "camera",
    "kya dekh",
    "kya dikh",
    "kya hai",
    "\u0915\u094d\u092f\u093e \u0926\u0947\u0916",
    "\u0915\u094d\u092f\u093e \u0926\u093f\u0916",
]
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
    "\u092a\u094d\u0930\u0938\u0941\u0937",
    "\u092a\u094d\u0930\u0938\u0941\u0937 \u0938\u0941\u0928\u094b",
    "\u0928\u092e\u0938\u094d\u0924\u0947 \u092a\u094d\u0930\u0938\u0941\u0937",
]
PROJECT_NAME = "PraSush"

BASE_DIR = Path(__file__).resolve().parent
AVATAR_PATH = BASE_DIR / AVATAR_IMAGE_PATH
MEMORY_PATH = BASE_DIR / "memory" / "history.json"
PROFILE_PATH = BASE_DIR / "memory" / "profile.json"
REMINDERS_PATH = BASE_DIR / "memory" / "reminders.json"
SCENE_IMAGE_PATH = BASE_DIR / "scene.jpg"

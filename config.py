from pathlib import Path

USE_VISION = False
AUTO_UNLOAD_VISION = True
MAX_MEMORY_CONTEXT = 5
AVATAR_IMAGE_PATH = "avatar.png"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
LOCAL_TIMEZONE = "Asia/Calcutta"

OLLAMA_ENDPOINT = "http://localhost:11434/api"
PHI3_MODEL = "phi3"
VISION_MODEL = "llava"

VISION_KEYWORDS = ["see", "look", "what is this", "describe", "camera"]
WAKE_WORD = "hey prasush"
WAKE_VARIANTS = [
    "hi",
    "hello",
    "hey",
    "hey pra",
    "hi pra",
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
SCENE_IMAGE_PATH = BASE_DIR / "scene.jpg"

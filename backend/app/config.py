import os
from pathlib import Path
from dotenv import load_dotenv

# Load env file from the backend folder
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_API_ENDPOINT = "https://integrate.api.nvidia.com/v1"
NVIDIA_TEXT_MODEL = os.getenv("NVIDIA_TEXT_MODEL", "google/gemma-3n-e2b-it")
NVIDIA_VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "microsoft/phi-4-multimodal-instruct")

FIREBASE_CONFIG = os.getenv("FIREBASE_CONFIG", "").strip()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Check if sandbox mode is active (i.e. no NVIDIA key is provided)
IS_SANDBOX_MODE = len(NVIDIA_API_KEY) == 0

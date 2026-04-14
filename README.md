# PraSush

PraSush is a Python prototype for an ambient AI assistant with:

- voice interaction using Whisper plus platform TTS
- a projector-style avatar UI using PyGame
- NVIDIA NIM for text reasoning and optional vision
- local reminders, rolling memory, and bilingual interaction

## Features

- NVIDIA-only model routing for simpler setup
- English, Hindi, and Hinglish support
- per-turn language replies instead of sticky mixed-language output
- dynamic speech capture that stops shortly after you stop speaking
- local reminders, date, and time handling
- optional camera-based vision using the NVIDIA vision model
- lighter logs with truncated prompts and responses

## Configuration

Important settings in `config.py`:

```python
USE_VISION = True
MAX_MEMORY_CONTEXT = 3
NVIDIA_TEXT_MODEL = "nvidia/llama-3.1-nemotron-ultra-253b-v1"
NVIDIA_VISION_MODEL = "microsoft/phi-4-multimodal-instruct"
WAKEWORD_MAX_RECORD_SECONDS = 2.5
QUERY_MAX_RECORD_SECONDS = 8.0
END_OF_SPEECH_SILENCE_SECONDS = 1.8
```

Set your NVIDIA key before running:

```powershell
$env:NVIDIA_API_KEY = "your-nvidia-api-key"
```

## Run

Run the desktop assistant:

```powershell
python main.py
```

Run the browser backend server for the web UI:

```powershell
python server.py
```

## Web UI and GitHub Pages

This repository now includes a browser-based UI under the `docs/` folder. You can deploy the `docs/` folder to GitHub Pages to access PraSush from any browser link.

- The web app can use a Python backend server for real provider integration.
- Users can choose between:
  - **Default NVIDIA provider** (configured in `docs/js/default-config.js`)
  - **Custom provider** with their own endpoint, model, and API key
- The avatar-style chat screen opens once a mode is selected.
- The browser supports text chat, microphone input, and camera-assisted vision requests.
- If the user asks a vision query such as "what do you see" or "describe the room", the page requests camera permission, captures the scene, and sends the image to the provider.
- If there is an API failure, the avatar displays the error message, the session ends, and the user can restart.
- The provider endpoint must support CORS for browser-based requests unless you are using the Python backend server.

### GitHub Pages deployment

1. In GitHub repo settings, enable GitHub Pages and select the `docs/` folder as the site source.
2. Place `docs/js/default-config.js` in the repo with your default NVIDIA settings if you want the default mode to work automatically.
3. If you want the web UI to call the Python backend instead of direct provider requests, run `python server.py` and update `window.PRA_SUSH_BACKEND_URL` in `docs/js/default-config.js` to the backend address.
4. Open the generated GitHub Pages URL.

### Notes

- For secure public deployment, do not publish a private API key in the static default config if it must remain secret.
- Use custom provider mode to allow users to enter their own endpoint, key, and model at runtime.
- Voice recognition uses the browser's SpeechRecognition API when available; camera capture uses `getUserMedia()`.

## Logging and configuration

By default the app writes INFO and higher logs. To enable debug-level logs, set:

```powershell
$env:PRA_SUSH_LOG_LEVEL = "DEBUG"
```

## What changed recently

- old Comet, Google, and Ollama routing was removed
- prompts were shortened to reduce latency
- logs were trimmed so they do not grow so aggressively
- Whisper now does one fast auto-detect pass instead of repeated forced-language retries
- replies follow the current user turn language by default
- wake and query recording now stop dynamically after speech ends

## Quick test

Try this sequence:

```text
Namaste
Mera naam Vedanshi hai
Kya kya kar sakte ho?
What time is it?
Hindi mein bolo
Aaj ki date kya hai?
Speak English
What do you see?
Stop
```

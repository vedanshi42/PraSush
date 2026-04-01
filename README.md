# PraSush

PraSush is a Python prototype for an ambient projector assistant that listens for a wake word, displays a fullscreen avatar UI, captures webcam frames for visual questions, and responds using a local LLM.

## Folder structure

- `main.py`
- `voice/` - microphone recording, speech recognition, and text-to-speech
- `vision/` - webcam capture and simple image description
- `llm/` - Ollama local model client
- `ui/` - fullscreen projector avatar and subtitle display
- `memory/` - recent interaction memory storage

## Setup

1. Create a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install the main dependencies:

```powershell
pip install pygame numpy sounddevice opencv-python pyttsx3 requests
```

3. Install Whisper locally:

- Option A: faster-whisper (recommended for performance)
  ```powershell
pip install faster-whisper
```

- Option B: openai-whisper
  ```powershell
pip install openai-whisper
```

4. If you choose `openai-whisper`, install `torch` as needed:

```powershell
pip install torch
```

## Install and run Ollama locally

1. Download and install Ollama from https://ollama.com.
2. Start Ollama with a compatible model, for example:

```powershell
ollama run llama2
```

3. Confirm the HTTP API is available at `http://127.0.0.1:11434`.

4. If your Ollama host differs, set:

```powershell
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
```

## How to connect a projector

- Connect the projector to your Windows machine as a second display.
- Set the projector as an extended or duplicate display.
- Run the app in fullscreen mode. The UI will fill the active screen.
- If you want to force the app to the projector, move the window there before starting.

## Running the app

```powershell
python main.py
```

## How it works

- The app continuously listens for the wake word `Hey PraSush`.
- When it detects the wake word, it activates a fullscreen black UI with an avatar and subtitles.
- It records a follow-up query, sends the combined prompt to Ollama, and speaks back the response.
- For visual questions, it captures a webcam image and includes a camera summary in the prompt.
- The last 5 interactions are kept in memory and are included in the assistant prompt.

## Notes

- The app is designed to work offline after installation.
- For best performance, install `faster-whisper` and a local Ollama model.
- Make sure your microphone and webcam are accessible from Python.

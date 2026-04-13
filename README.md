# PraSush

PraSush is a production-oriented Python prototype for an ambient AI assistant with:

- voice interaction using Whisper plus platform TTS
- projector-style fullscreen avatar UI using PyGame
- NVIDIA NIM for normal text reasoning and optional vision
- optional LLaVA on Ollama for on-demand vision
- strict RAM-aware behavior so the vision model is not kept loaded unless required

## Features

- Uses NVIDIA NIM for normal text conversation turns when `LLM_PROVIDER = "nvidia"`
- Can use CometAPI if `LLM_PROVIDER = "cometapi"`
- Can still use Ollama text mode if `LLM_PROVIDER = "ollama"`
- Uses LLaVA only when a visual query is detected
- Captures an image only when vision is needed and saves it as `scene.jpg`
- Unloads LLaVA after the response when `AUTO_UNLOAD_VISION = True`
- Logs `[MODEL USED]`, `[RAW RESPONSE]`, and `[PARSED RESPONSE]` on every model call
- Maintains the last 5 user/assistant exchanges in persistent local memory
- Stores local reminders and announces them when due
- Supports English, Hindi, and Hinglish voice queries through Whisper auto-detection
- Drives an avatar through `idle`, `listening`, `thinking`, `speaking`, and `greeting` states
- Starts in a normal window for easier testing, with `F` to toggle fullscreen
- Asks your name on first use and remembers it for later conversations

## Project structure

- `main.py` - main assistant loop
- `config.py` - runtime configuration
- `llm/client.py` - NVIDIA, CometAPI, Google, and Ollama model calls with debug logging
- `voice/recognizer.py` - Whisper STT and platform-aware TTS
- `vision/camera.py` - on-demand OpenCV capture
- `ui/display.py` - fullscreen projector avatar UI
- `memory/store.py` - persistent rolling conversation memory
- `memory/reminders.py` - local reminder storage and simple natural-time parsing

## Configuration

Edit `config.py`:

```python
LLM_PROVIDER = "nvidia"
USE_VISION = False
AUTO_UNLOAD_VISION = True
MAX_MEMORY_CONTEXT = 5
AVATAR_IMAGE_PATH = "avatar.png"
```

Important notes:

- Set the environment variable `NVIDIA_API_KEY` before running PraSush in NVIDIA mode.
- `NVIDIA_TEXT_MODEL` defaults to `nvidia/nemotron-4-mini-hindi-4b-instruct`.
- `NVIDIA_VISION_MODEL` defaults to `microsoft/phi-4-multimodal-instruct`.
- `COMET_MODEL` defaults to `gemini-2.5-flash`, which matches the earlier working setup, and you can override it with an environment variable if your Comet account supports another model.
- If you receive a `403 Forbidden` error, verify that your Comet API key is valid, has permission for the selected model, and that the selected `COMET_MODEL` is supported by your key.
- Put your avatar image at `avatar.png` in the project root, or update `AVATAR_IMAGE_PATH`.
- `USE_VISION = False` disables camera capture and LLaVA routing.
- When `LLM_PROVIDER = "cometapi"` and `USE_VISION = True`, PraSush can send camera images through CometAPI using the configured multimodal model.
- `AUTO_UNLOAD_VISION = True` keeps RAM usage lower on 8-16 GB systems.
- `STT_LANGUAGE = None` lets Whisper auto-detect English, Hindi, and Hinglish. Set it to `"en"` or `"hi"` only if you want to force one language.

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Set the NVIDIA key

For the current PowerShell session:
```powershell
$env:NVIDIA_API_KEY = "your-nvidia-api-key"
```

Or create a local `.env` file in the project root:
```text
NVIDIA_API_KEY=your-nvidia-api-key
NVIDIA_TEXT_MODEL=nvidia/nemotron-4-mini-hindi-4b-instruct
NVIDIA_VISION_MODEL=microsoft/phi-4-multimodal-instruct
```

PraSush also checks Windows User and Machine environment variables directly. If you want to keep Comet as a fallback, you can still set `COMET_API_KEY` and `COMET_MODEL` too.

### 4. Optional: install Ollama for later local vision testing

Install Ollama from [https://ollama.com/download](https://ollama.com/download).

### 5. Optional: pull the local vision models

```powershell
ollama run phi3
ollama run llava
```

After each model finishes loading once, you can exit that interactive session with `Ctrl+C`.

### 6. Confirm Ollama API access if you plan to test vision

PraSush uses:

- `http://localhost:11434/api/generate`

Make sure the Ollama service is running before you launch PraSush.

## Running PraSush

```powershell
python main.py
```

PraSush opens in a normal window by default so it is easier to test and switch screens.

- Press `F` to toggle fullscreen projector mode
- Press `Esc` to close the app

## Voice and decision flow

1. PraSush listens continuously for `hey prasush`
2. When detected, avatar state changes to `greeting`
3. PraSush introduces itself as PraSush and greets you
4. It records the next spoken query
5. If the query contains a vision keyword, it captures `scene.jpg` and routes to LLaVA
6. Otherwise, it routes to the configured text provider
7. Avatar changes to `thinking`, then `speaking`
8. The response is spoken aloud and stored in memory
9. UI returns to `idle`

PraSush also handles a few simple local actions directly:

- current time
- today's date
- local reminders

## Vision trigger keywords

PraSush treats the query as visual if it contains one of:

- `see`
- `look`
- `what is this`
- `describe`
- `camera`

## RAM-aware behavior

- NVIDIA is the default text provider in the current configuration
- LLaVA is only called for visual prompts
- When `AUTO_UNLOAD_VISION = True`, PraSush explicitly asks Ollama to release LLaVA after the response
- This behavior is intended for low-resource systems where leaving a vision model resident is too expensive

## Debug logging

For every LLM request, PraSush prints:

- `[MODEL USED]`
- `[RAW RESPONSE]`
- `[PARSED RESPONSE]`

For failures, PraSush prints explicit `[ERROR]` logs and raises errors instead of silently falling back.

Backend logs are also written to the `logs/` folder so you can share the latest `.log` file when debugging microphone, transcription, or model issues.

## Detailed test run instructions

### Test 1. Basic startup

```powershell
python main.py
```

Expected result:

- a normal window opens first
- avatar is visible in the center
- top status shows PraSush in `Idle`
- bottom subtitle says to say `Hey PraSush`
- pressing `F` switches between windowed and fullscreen mode

### Test 2. Wake word flow

Say:

```text
Hey PraSush
```

Expected result:

- UI switches to `Greeting`
- subtitle shows a hello message
- PraSush introduces itself and responds with a greeting
- UI then switches to `Listening`

### Test 3. Normal NVIDIA reasoning flow

After the wake word, say:

```text
What can you help me with?
```

Expected result:

- UI switches to `Thinking`
- terminal logs show:
  - `[MODEL USED] NVIDIA`
  - `[RAW RESPONSE] ...`
  - `[PARSED RESPONSE] ...`
- UI switches to `Speaking`
- PraSush speaks the NVIDIA answer

### Test 4. Vision flow

After the wake word, say:

```text
What do you see?
```

Expected result:

- OpenCV captures a webcam frame
- `scene.jpg` is created in the project root
- terminal logs show either:
  - `[MODEL USED] NVIDIA Vision`
  - or `[MODEL USED] LLaVA`
- if Ollama LLaVA is being used and `AUTO_UNLOAD_VISION = True`, terminal also shows:
  - `[MODEL] Unloading LLaVA to save RAM`

### Test 5. Memory context

Ask 2-3 normal questions in sequence, for example:

```text
Hey PraSush
My name is Vedanshi.
```

Then:

```text
Hey PraSush
What is my name?
```

Expected result:

- PraSush includes recent conversation context in the prompt
- the stored history is written to `memory/history.json`
- only the last 5 exchanges are preserved

### Test 6. Vision disabled mode

Set in `config.py`:

```python
USE_VISION = False
```

Then run:

```powershell
python main.py
```

Ask:

```text
Hey PraSush
What do you see?
```

Expected result:

- no camera capture occurs
- no LLaVA call occurs
- NVIDIA handles the request as a plain text query

### NVIDIA only quick test

If you want to test only cloud text mode first, keep in `config.py`:

```python
LLM_PROVIDER = "nvidia"
USE_VISION = False
```

Then run:

```powershell
python main.py
```

Ask simple questions like:

```text
Hi
What is today's date?
What time is it?
Who are you?
Namaste
Abhi kya time hai?
Hindi mein batao, tum kya kar sakti ho?
```

### Test 7. Missing camera failure

If no webcam is available, ask a visual question.

Expected result:

- PraSush prints an explicit `[ERROR] Vision capture failed: ...`
- the failure is visible in the terminal
- there is no silent fallback

### Test 8. Ollama service failure

Stop Ollama, then run:

```powershell
python main.py
```

Ask any question after the wake word.

Expected result:

- PraSush prints an explicit `[ERROR] Ollama request failed: ...`
- the error is not hidden

## Demo script

1. Say `Hey PraSush`
2. Ask `What can you do?`
3. Say `Hey PraSush`
4. Ask `What do you see?`

This demonstrates:

- wake word activation
- Phi-3 reasoning
- on-demand LLaVA vision
- avatar state transitions
- RAM-aware LLaVA unload behavior

## Troubleshooting

- If speech input fails, confirm the microphone works and is accessible to Python.
- On Windows, PraSush uses PowerShell/System.Speech for TTS by default.
- On macOS, PraSush uses the built-in `say` command for TTS.
- If the UI does not show the intended character, place your image at `avatar.png`.
- If vision requests fail, test the webcam separately in another app first.
- If Ollama requests fail, ensure both `phi3` and `llava` are installed locally.

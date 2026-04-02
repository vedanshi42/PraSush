# PraSush

PraSush is a production-oriented Python prototype for an ambient AI assistant with:

- voice interaction using Whisper plus `pyttsx3`
- projector-style fullscreen avatar UI using PyGame
- Phi-3 on Ollama for normal reasoning
- optional LLaVA on Ollama for on-demand vision
- strict RAM-aware behavior so the vision model is not kept loaded unless required

## Features

- Uses Phi-3 for every normal conversation turn
- Uses LLaVA only when a visual query is detected
- Captures an image only when vision is needed and saves it as `scene.jpg`
- Unloads LLaVA after the response when `AUTO_UNLOAD_VISION = True`
- Logs `[MODEL USED]`, `[RAW RESPONSE]`, and `[PARSED RESPONSE]` on every model call
- Maintains the last 5 user/assistant exchanges in persistent local memory
- Drives an avatar through `idle`, `listening`, `thinking`, `speaking`, and `greeting` states
- Starts in a normal window for easier testing, with `F` to toggle fullscreen
- Asks your name on first use and remembers it for later conversations

## Project structure

- `main.py` - main assistant loop
- `config.py` - runtime configuration
- `llm/client.py` - Phi-3 and LLaVA Ollama calls with debug logging
- `voice/recognizer.py` - Whisper STT and `pyttsx3` TTS
- `vision/camera.py` - on-demand OpenCV capture
- `ui/display.py` - fullscreen projector avatar UI
- `memory/store.py` - persistent rolling conversation memory

## Configuration

Edit `config.py`:

```python
USE_VISION = True
AUTO_UNLOAD_VISION = True
MAX_MEMORY_CONTEXT = 5
AVATAR_IMAGE_PATH = "avatar.png"
```

Important notes:

- Put your avatar image at `avatar.png` in the project root, or update `AVATAR_IMAGE_PATH`.
- `USE_VISION = False` disables camera capture and LLaVA routing.
- `AUTO_UNLOAD_VISION = True` keeps RAM usage lower on 8-16 GB systems.

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

### 3. Install Ollama

Install Ollama from [https://ollama.com/download](https://ollama.com/download).

### 4. Pull the required local models

```powershell
ollama run phi3
ollama run llava
```

After each model finishes loading once, you can exit that interactive session with `Ctrl+C`.

### 5. Confirm Ollama API access

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
6. Otherwise, it routes to Phi-3
7. Avatar changes to `thinking`, then `speaking`
8. The response is spoken aloud and stored in memory
9. UI returns to `idle`

## Vision trigger keywords

PraSush treats the query as visual if it contains one of:

- `see`
- `look`
- `what is this`
- `describe`
- `camera`

## RAM-aware behavior

- Phi-3 is the default assistant model
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

### Test 3. Normal Phi-3 reasoning flow

After the wake word, say:

```text
What can you help me with?
```

Expected result:

- UI switches to `Thinking`
- terminal logs show:
  - `[MODEL USED] Phi-3`
  - `[RAW RESPONSE] ...`
  - `[PARSED RESPONSE] ...`
- UI switches to `Speaking`
- PraSush speaks the Phi-3 answer

### Test 4. Vision flow with LLaVA

After the wake word, say:

```text
What do you see?
```

Expected result:

- OpenCV captures a webcam frame
- `scene.jpg` is created in the project root
- terminal logs show:
  - `[MODEL USED] LLaVA`
  - `[RAW RESPONSE] ...`
  - `[PARSED RESPONSE] ...`
- if `AUTO_UNLOAD_VISION = True`, terminal also shows:
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
- Phi-3 handles the request as a plain text query

### Phi-3 only quick test

If you want to test only Phi-3 first, set in `config.py`:

```python
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
- If speech output fails, verify the Windows TTS engine is available for `pyttsx3`.
- If the UI does not show the intended character, place your image at `avatar.png`.
- If vision requests fail, test the webcam separately in another app first.
- If Ollama requests fail, ensure both `phi3` and `llava` are installed locally.

# PraSush Recent Improvements - Testing Guide

## What's New

### 1. **Comprehensive Logging System**
All operations are now logged to both console and file for complete visibility.

**Log Files Location:** `logs/` folder in your project
- New log file created each time you run the app
- Format: `prasush_YYYYMMDD_HHMMSS.log`

**What's Logged:**
- App initialization and startup
- Voice recognition (transcriptions)
- LLM requests and responses (full prompts and answers)
- Speech synthesis (text being spoken)
- Camera operations
- Memory/conversation context
- All errors with full stack traces

**To Check Logs:**
```powershell
# After running the app, check the latest log
Get-ChildItem logs/ -Latest 1 | Get-Content -Tail 50
```

---

### 2. **Windowed Mode by Default**
The app now starts in a resizable window instead of fullscreen, so you can easily test and debug.

**Controls:**
- **F Key**: Toggle fullscreen on/off
- **ESC**: Quit the app
- Window title shows these controls

**Benefits:**
- Easy to see console output and errors
- Can switch between windows while testing
- Can resize to any size you want
- Press F when ready to go fullscreen

---

### 3. **Improved Conversation Intelligence**

#### Time/Date Awareness
The model now knows the current time and date, so you can ask:
- "What time is it?"
- "What's today's date?"
- "How long until 5 PM?"

The prompt now includes: `Current time: HH:MM AM/PM, Date: Day, Month DD, YYYY`

#### Better Prompt Engineering
- Clear instructions for conversational tone
- Explicitly tells model to be adaptable
- Includes memory context automatically
- Better visual description format

#### Improved Face Detection
- More sensitive parameters (was too strict)
- Now should detect faces at various distances
- Better in varied lighting conditions

**Test Commands:**
```
1. Say: "Hey PraSush, what time is it?"
2. Say: "Hey PraSush, what's the date?"
3. Say: "Hey PraSush, tell me a joke"
4. Say: "Hey PraSush, do you remember what I just asked?"
```

---

### 4. **Better Error Handling**

**Before:** Errors silently failed
**Now:** All errors are:
- Logged with full details
- Displayed in console
- Tracked in log files
- User-friendly error messages in the UI

**Common Error Messages & Solutions:**

```
"Could not connect to Ollama"
→ Solution: Run 'ollama run phi3' in another terminal first

"LLM request timed out"
→ Solution: Close other apps to free RAM, try again

"No audio data to transcribe"
→ Solution: Check microphone is working, speak clearly

"Failed to capture camera frame"
→ Solution: Check camera permissions and connectivity
```

---

### 5. **Memory/Conversation Improvements**

**What's Tracked:**
- Last 5 user queries
- Last 5 assistant responses
- Stored in `memory/history.json`

**Improvements:**
- Logs every memory update
- Shows context being used in each request
- Can verify conversations are being maintained

**Check Memory:**
```powershell
cat memory/history.json
```

---

## Testing Checklist

### ✅ Setup
- [ ] Run: `python main.py`
- [ ] App starts in windowed mode
- [ ] Title bar shows "PraSush - Press F for fullscreen, ESC to quit"

### ✅ Time/Date
- [ ] Say: "Hey PraSush, what time is it?"
- [ ] Response should include current time
- [ ] Check logs show the LLM response

### ✅ Conversation Flow
- [ ] Say: "Hey PraSush, what's your name?"
- [ ] Say: "Hey PraSush, who am I talking to?"
- [ ] App should remember previous question (memory context)
- [ ] Response should flow naturally

### ✅ Logging
- [ ] Check `logs/` folder has new files
- [ ] Open latest log file
- [ ] Verify you see:
  - Initialization messages
  - Speech recognition output
  - LLM request/response
  - Speech synthesis logs
  - No errors (or errors with explanations)

### ✅ Face Detection
- [ ] Say: "Hey PraSush, can you see me?"
- [ ] Sit in front of camera
- [ ] Response should mention "1 person detected" or similar
- [ ] Works at different distances/lighting

### ✅ Display
- [ ] Press F to toggle fullscreen
- [ ] Window resizes smoothly
- [ ] Avatar animations show thinking/listening/speaking
- [ ] Subtitles display correctly

### ✅ Error Handling
- [ ] Disconnect camera and ask visual question → see helpful error
- [ ] Close Ollama and ask a question → see connection error with solution
- [ ] All errors appear in both console and log file

---

## How to Debug

### 1. **Check What Phi3 is Hearing**
```
Watch the console when you speak. You should see:
"INFO - Transcribed (faster-whisper): [what you said]"
```

### 2. **Check What Phi3 is Responding**
Look for in logs:
```
INFO - LLM Response:
[The full multi-line response from the model]
```

### 3. **Check If Speech is Being Spoken**
Look for:
```
INFO - Speaking: [text being spoken]
```

### 4. **View Complete Request/Response Cycle**
In your latest log file, search for "LLM Request" to see:
- What prompt was sent
- What the model received as context
- What time/date info was included

### 5. **Check Memory Context**
```
DEBUG - Memory context: User: ...
```

---

## Troubleshooting

### Issue: "Phi3 keeps timing out"
**Cause:** Not enough free RAM (~322 MB available, need ~2 GB)
**Solution:**
1. Close all unnecessary apps/browsers
2. Increase timeout from 120 to 180 seconds:
   ```python
   # In llm/client.py, change:
   response = requests.post(..., timeout=180)
   ```

### Issue: "Can't see my face even though I'm in front of camera"
**Cause:** Face detection parameters were tuned, but environment might be dark
**Solution:**
1. Improve lighting (use lamp, face window)
2. Get closer to camera
3. Check `logs/` to see if faces are being detected (DEBUG logs)

### Issue: "Model keeps giving same default response"
**Cause:** Memory not persisting OR model not receiving context
**Solution:**
1. Check `logs/` for "Memory context" log lines
2. Delete `memory/history.json` to start fresh
3. Check if the LLM request includes recent memory

### Issue: "Speech synthesis not working"
**Cause:** pyttsx3 might not have engines available
**Solution:**
```powershell
# Reinstall pyttsx3
pip uninstall pyttsx3
pip install pyttsx3
```

---

## Performance Tips

1. **Faster Responses:**
   - Reduce max_tokens from 400 to 300 in `llm/client.py`
   - Clear background tasks/apps

2. **Better Face Detection:**
   - Use good lighting
   - Sit 2-3 feet from camera
   - Face camera directly

3. **Clearer Speech Recognition:**
   - Speak clearly and at normal volume
   - Quiet environment
   - Microphone close to you

4. **Lower Memory Usage:**
   - Close browser/heavy apps before running
   - Use phi3 (currently using it - best for 8GB RAM)

---

## File Locations

```
PraSush/
├── logs/                    # ← New! Check here for debugging
│   ├── prasush_20260401_123456.log
│   └── prasush_20260401_123500.log
├── llm/
│   └── client.py           # ← Updated: Better logging & error handling
├── voice/
│   └── recognizer.py       # ← Updated: Logs transcriptions
├── vision/
│   └── camera.py           # ← Updated: Better face detection & logging
├── ui/
│   └── display.py          # ← Updated: Windowed mode, F key toggle
├── memory/
│   ├── history.json        # Your conversation history
│   └── store.py            # ← Updated: Memory logging
├── main.py                 # ← Updated: Time awareness, logging
├── logger.py               # ← New! Centralized logging
├── AVATAR_CUSTOMIZATION.md # ← New! Guide for custom avatar
└── README.md               # Original setup guide
```

---

## Next Steps

1. **Test everything** using the checklist above
2. **Check logs** to understand what's happening
3. **Share custom avatar image** when ready (PNG recommended)
4. **Report any issues** with details from logs

---

## Key Commands for Testing

```powershell
# Run the app with logging
cd c:\Users\prave\Documents\PraSush
.\.venv\Scripts\Activate.ps1
ollama run phi3                    # In one terminal
python main.py                     # In another terminal

# Monitor logs in real-time
Get-Content logs/prasush_*.log -Wait

# Check recent memory
cat memory/history.json | ConvertFrom-Json | ForEach-Object { $_ }

# Clear history and start fresh
Remove-Item memory/history.json
Remove-Item logs/*
```

---

## Questions?

Check logs first - they usually contain the answer! If stuck:
1. Check the latest log file
2. Search for ERROR or exception
3. Share that section for diagnosis

All changes are backward compatible - existing code still works!

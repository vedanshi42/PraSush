import time
import os
import threading
import numpy as np
import sounddevice as sd
import pyttsx3
from logger import app_logger

try:
    from faster_whisper import WhisperModel
    HAS_FAST_WHISPER = True
except Exception:
    HAS_FAST_WHISPER = False

try:
    import whisper
    HAS_OPENAI_WHISPER = True
except Exception:
    HAS_OPENAI_WHISPER = False


class SpeechRecognizer:
    def __init__(self, model_name="small", sample_rate=16000):
        self.sample_rate = sample_rate
        self.model_name = model_name
        self.model = self._load_model()
        app_logger.info(f"Speech recognizer initialized with model: {model_name}")

    def _load_model(self):
        if HAS_FAST_WHISPER:
            app_logger.info("Using faster-whisper for speech recognition")
            return WhisperModel(self.model_name, device="cpu", compute_type="int8")
        if HAS_OPENAI_WHISPER:
            app_logger.info("Using openai-whisper for speech recognition")
            return whisper.load_model(self.model_name)
        raise RuntimeError(
            "No Whisper model available. Install faster-whisper or openai-whisper to enable speech recognition."
        )

    def record(self, duration=3):
        app_logger.debug(f"Recording audio for {duration} seconds")
        frames = int(duration * self.sample_rate)
        recording = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="float32")
        sd.wait()
        return np.squeeze(recording)

    def transcribe(self, audio):
        if audio is None or len(audio) == 0:
            app_logger.warning("No audio data to transcribe")
            return ""
        if HAS_FAST_WHISPER:
            segments, _ = self.model.transcribe(audio, beam_size=5, language="en")
            result = " ".join(segment.text.strip() for segment in segments).strip()
            app_logger.info(f"Transcribed (faster-whisper): {result}")
            return result
        if HAS_OPENAI_WHISPER:
            result = self.model.transcribe(audio, language="en")
            text = result.get("text", "").strip()
            app_logger.info(f"Transcribed (openai-whisper): {text}")
            return text
        return ""

    def listen_for_wakeword(self):
        try:
            audio = self.record(duration=3)
            text = self.transcribe(audio).lower()
            return text
        except Exception as e:
            app_logger.error(f"Error listening for wakeword: {e}")
            return ""

    def record_query(self):
        try:
            audio = self.record(duration=6)
            return self.transcribe(audio)
        except Exception as e:
            app_logger.error(f"Error recording query: {e}")
            return ""


class SpeechSynthesizer:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Try to set the best available voice
        try:
            self.engine.setProperty("rate", 150)  # Speed
            self.engine.setProperty("volume", 1.0)  # Volume max
            
            # Get available voices and use the first one (usually works best)
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
            
            app_logger.info(f"Speech synthesizer initialized with {len(voices)} voices available")
        except Exception as e:
            app_logger.warning(f"Could not configure voices: {e}")
            app_logger.info("Speech synthesizer initialized with default settings")
        
        self.is_speaking = False

    def speak_async(self, text):
        """Speak in a separate thread so it doesn't block UI"""
        if not text:
            return

        if self.is_speaking:
            app_logger.info("Interrupting previous speech for new output")
            try:
                self.engine.stop()
            except Exception as e:
                app_logger.warning(f"Could not stop previous speech cleanly: {e}")

        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()

    def _speak_sync(self, text):
        """Internal method that actually does the speaking"""
        if not text:
            app_logger.debug("No text to speak")
            return
        
        try:
            self.is_speaking = True
            text_preview = text[:80] + "..." if len(text) > 80 else text
            app_logger.info(f"Speaking: {text_preview}")
            
            # Clear any previous speech
            self.engine.stop()
            
            # Add the text and speak
            self.engine.say(text)
            
            # This blocks until speech is complete
            app_logger.debug("Waiting for speech synthesis...")
            self.engine.runAndWait()
            
            app_logger.debug("Speech synthesis completed")
        except Exception as e:
            app_logger.error(f"Speech synthesis error: {e}")
        finally:
            self.is_speaking = False

    def speak(self, text):
        """Public method - use async speaking"""
        self.speak_async(text)


class VoiceAssistant:
    def __init__(self):
        self.recognizer = SpeechRecognizer()
        self.synthesizer = SpeechSynthesizer()

    def listen_for_wakeword(self):
        return self.recognizer.listen_for_wakeword()

    def record_query(self):
        return self.recognizer.record_query()

    def speak(self, text):
        self.synthesizer.speak(text)

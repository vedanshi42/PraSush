import time
import os
import numpy as np
import sounddevice as sd
import pyttsx3

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

    def _load_model(self):
        if HAS_FAST_WHISPER:
            return WhisperModel(self.model_name, device="cpu", compute_type="int8")
        if HAS_OPENAI_WHISPER:
            return whisper.load_model(self.model_name)
        raise RuntimeError(
            "No Whisper model available. Install faster-whisper or openai-whisper to enable speech recognition."
        )

    def record(self, duration=3):
        frames = int(duration * self.sample_rate)
        recording = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="float32")
        sd.wait()
        return np.squeeze(recording)

    def transcribe(self, audio):
        if audio is None or len(audio) == 0:
            return ""
        if HAS_FAST_WHISPER:
            segments, _ = self.model.transcribe(audio, beam_size=5, language="en")
            return " ".join(segment.text.strip() for segment in segments).strip()
        if HAS_OPENAI_WHISPER:
            result = self.model.transcribe(audio, language="en")
            return result.get("text", "").strip()
        return ""

    def listen_for_wakeword(self):
        try:
            audio = self.record(duration=3)
            text = self.transcribe(audio).lower()
            return text
        except Exception:
            return ""

    def record_query(self):
        try:
            audio = self.record(duration=6)
            return self.transcribe(audio)
        except Exception:
            return ""


class SpeechSynthesizer:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)

    def speak(self, text):
        if not text:
            return
        self.engine.say(text)
        self.engine.runAndWait()


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

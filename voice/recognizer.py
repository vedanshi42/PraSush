from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pyttsx3
import sounddevice as sd
import soundfile as sf
from logger import app_logger

try:
    from faster_whisper import WhisperModel
except ImportError as exc:
    raise RuntimeError("faster-whisper is required for PraSush voice input.") from exc


class SpeechRecognizer:
    def __init__(self, model_name: str = "base", sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
        app_logger.info(f"Speech recognizer initialized with Whisper model '{model_name}' at {sample_rate} Hz")

    def record(self, duration: int = 3) -> Path:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as handle:
            file_path = Path(handle.name)

        app_logger.info(f"Recording audio for {duration} seconds")
        frames = int(duration * self.sample_rate)
        recording = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="float32")
        sd.wait()
        sf.write(file_path, recording, self.sample_rate)
        app_logger.debug(f"Audio saved temporarily to {file_path}")
        return file_path

    def transcribe(self, audio_path: Path) -> str:
        try:
            segments, _ = self.model.transcribe(str(audio_path), beam_size=5, language="en", vad_filter=True)
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            app_logger.info(f"Transcript: {transcript or '[empty]'}")
            return transcript
        finally:
            try:
                audio_path.unlink(missing_ok=True)
            except OSError as exc:
                print(f"[ERROR] Failed to delete temporary audio file: {exc}")
                app_logger.error(f"Failed to delete temporary audio file {audio_path}: {exc}")

    def listen_for_wakeword(self) -> str:
        try:
            audio = self.record(duration=2)
            transcript = self.transcribe(audio).lower()
            app_logger.info(f"Wake transcript: {transcript or '[empty]'}")
            return transcript
        except Exception as exc:
            print(f"[ERROR] Wake word transcription failed: {exc}")
            app_logger.error(f"Wake word transcription failed: {exc}")
            return ""

    def record_query(self) -> str:
        try:
            audio = self.record(duration=8)
            transcript = self.transcribe(audio)
            app_logger.info(f"Query transcript: {transcript or '[empty]'}")
            return transcript
        except Exception as exc:
            print(f"[ERROR] Query transcription failed: {exc}")
            app_logger.error(f"Query transcription failed: {exc}")
            return ""


class SpeechSynthesizer:
    def __init__(self) -> None:
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)
        self._is_speaking = False

    def speak(self, text: str) -> None:
        if not text:
            return
        app_logger.info(f"TTS speaking: {text[:200]}")
        self._is_speaking = True
        self.engine.say(text)
        self.engine.runAndWait()
        self._is_speaking = False
        time.sleep(0.6)

    def is_speaking(self) -> bool:
        return self._is_speaking

    def wait_until_done(self) -> None:
        return None


class VoiceAssistant:
    def __init__(self) -> None:
        self.recognizer = SpeechRecognizer()
        self.synthesizer = SpeechSynthesizer()

    def listen_for_wakeword(self) -> str:
        return self.recognizer.listen_for_wakeword()

    def record_query(self) -> str:
        return self.recognizer.record_query()

    def speak(self, text: str) -> None:
        self.synthesizer.speak(text)

    def is_speaking(self) -> bool:
        return self.synthesizer.is_speaking()

    def wait_until_done(self) -> None:
        self.synthesizer.wait_until_done()

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import sounddevice as sd
import soundfile as sf
import pyttsx3
from logger import app_logger

try:
    from faster_whisper import WhisperModel
except ImportError as exc:
    raise RuntimeError("faster-whisper is required for PraSush voice input.") from exc


class SpeechRecognizer:
    def __init__(self, model_name: str = "base", sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def record(self, duration: int = 3) -> Path:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as handle:
            file_path = Path(handle.name)

        frames = int(duration * self.sample_rate)
        recording = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="float32")
        sd.wait()
        sf.write(file_path, recording, self.sample_rate)
        return file_path

    def transcribe(self, audio_path: Path) -> str:
        try:
            segments, _ = self.model.transcribe(str(audio_path), beam_size=5, language="en", vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            try:
                audio_path.unlink(missing_ok=True)
            except OSError as exc:
                print(f"[ERROR] Failed to delete temporary audio file: {exc}")

    def listen_for_wakeword(self) -> str:
        try:
            audio = self.record(duration=2)
            return self.transcribe(audio).lower()
        except Exception as exc:
            print(f"[ERROR] Wake word transcription failed: {exc}")
            return ""

    def record_query(self) -> str:
        try:
            audio = self.record(duration=6)
            return self.transcribe(audio)
        except Exception as exc:
            print(f"[ERROR] Query transcription failed: {exc}")
            return ""


class SpeechSynthesizer:
    def __init__(self) -> None:
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)
        self._lock = threading.Lock()
        self._is_speaking = threading.Event()
        self._worker: threading.Thread | None = None

    def speak(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            self._is_speaking.set()
            self.engine.say(text)
            self.engine.runAndWait()
            self._is_speaking.clear()

    def speak_async(self, text: str) -> None:
        self.wait_until_done()
        self._is_speaking.set()
        self._worker = threading.Thread(target=self.speak, args=(text,), daemon=True)
        self._worker.start()

    def is_speaking(self) -> bool:
        return self._is_speaking.is_set()

    def wait_until_done(self) -> None:
        if self._worker and self._worker.is_alive():
            self._worker.join()


class VoiceAssistant:
    def __init__(self) -> None:
        self.recognizer = SpeechRecognizer()
        self.synthesizer = SpeechSynthesizer()

    def listen_for_wakeword(self) -> str:
        return self.recognizer.listen_for_wakeword()

    def record_query(self) -> str:
        return self.recognizer.record_query()

    def speak(self, text: str) -> None:
        self.synthesizer.speak_async(text)

    def is_speaking(self) -> bool:
        return self.synthesizer.is_speaking()

    def wait_until_done(self) -> None:
        self.synthesizer.wait_until_done()

from __future__ import annotations

import platform
import tempfile
import time
from pathlib import Path
import subprocess
import base64

import pyttsx3
import sounddevice as sd
import soundfile as sf
from config import TTS_PITCH, TTS_RATE, TTS_VOICE_MAC
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
            audio = self.record(duration=6)
            transcript = self.transcribe(audio)
            app_logger.info(f"Query transcript: {transcript or '[empty]'}")
            return transcript
        except Exception as exc:
            print(f"[ERROR] Query transcription failed: {exc}")
            app_logger.error(f"Query transcription failed: {exc}")
            return ""


class SpeechSynthesizer:
    def __init__(self) -> None:
        self.engine = None
        self.backend = self._select_backend()
        self._is_speaking = False
        self._active_process: subprocess.Popen[str] | None = None
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 150)
            self.engine.setProperty("volume", 1.0)
            app_logger.info("pyttsx3 initialized successfully")
        except Exception as exc:
            self.engine = None
            app_logger.error(f"pyttsx3 initialization failed: {exc}")
            if self.backend == "pyttsx3":
                self.backend = "powershell" if platform.system() == "Windows" else "say"
        app_logger.info(f"TTS backend selected: {self.backend}")

    def start_speaking(self, text: str) -> None:
        if not text:
            return
        app_logger.info(f"TTS speaking via {self.backend}: {text[:200]}")
        self._is_speaking = True
        try:
            if self.backend == "powershell":
                self._active_process = self._start_powershell_tts(text)
            elif self.backend == "say":
                self._active_process = self._start_macos_say(text)
            elif self.backend == "pyttsx3" and self.engine is not None:
                self.engine.say(text)
                self.engine.runAndWait()
                self._is_speaking = False
            else:
                raise RuntimeError(f"Unsupported TTS backend '{self.backend}'")
        except Exception as exc:
            app_logger.error(f"TTS playback failed: {exc}")
            self._is_speaking = False
            self._active_process = None

    def speak(self, text: str) -> None:
        self.start_speaking(text)
        self.wait_until_done()

    def is_speaking(self) -> bool:
        if self._active_process is not None:
            running = self._active_process.poll() is None
            self._is_speaking = running
            if not running:
                stdout = self._active_process.stdout.read().strip() if self._active_process.stdout else ""
                stderr = self._active_process.stderr.read().strip() if self._active_process.stderr else ""
                if stdout:
                    app_logger.debug(f"TTS stdout: {stdout}")
                if stderr:
                    app_logger.warning(f"TTS stderr: {stderr}")
                self._active_process = None
        return self._is_speaking

    def wait_until_done(self) -> None:
        while self.is_speaking():
            time.sleep(0.05)
        time.sleep(0.25)

    def _select_backend(self) -> str:
        system = platform.system()
        if system == "Windows":
            return "powershell"
        if system == "Darwin":
            return "say"
        return "pyttsx3"

    def _start_powershell_tts(self, text: str) -> subprocess.Popen[str]:
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pitch = TTS_PITCH.replace('"', "")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            f"$pitch = '{pitch}'; "
            f"$raw = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{base64.b64encode(safe_text.encode('utf-8')).decode('ascii')}')); "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {TTS_RATE}; "
            "$s.Volume = 100; "
            "$ssml = \"<speak version='1.0' xml:lang='en-US'><prosody pitch='$pitch'>$raw</prosody></speak>\"; "
            "$s.SpeakSsml($ssml)"
        )
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _start_macos_say(self, text: str) -> subprocess.Popen[str]:
        return subprocess.Popen(
            ["say", "-v", TTS_VOICE_MAC, "-r", "210", text],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


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

    def start_speaking(self, text: str) -> None:
        self.synthesizer.start_speaking(text)

    def is_speaking(self) -> bool:
        return self.synthesizer.is_speaking()

    def wait_until_done(self) -> None:
        self.synthesizer.wait_until_done()

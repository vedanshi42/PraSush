from __future__ import annotations

import base64
import platform
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import pyttsx3
import pygame
import sounddevice as sd
import soundfile as sf
import numpy as np
from config import (
    END_OF_SPEECH_SILENCE_SECONDS,
    MIN_SPEECH_SECONDS,
    QUERY_MAX_RECORD_SECONDS,
    SPEECH_SILENCE_THRESHOLD,
    SPEECH_START_THRESHOLD,
    STT_INITIAL_PROMPT,
    TTS_ENABLE_GTTS,
    TTS_PITCH,
    TTS_RATE,
    TTS_VOICE_MAC,
    WAKEWORD_MAX_RECORD_SECONDS,
    WHISPER_MODEL_NAME,
)
from logger import app_logger

try:
    from faster_whisper import WhisperModel
except ImportError as exc:
    raise RuntimeError("faster-whisper is required for PraSush voice input.") from exc

try:
    from gtts import gTTS
except ImportError:
    gTTS = None


@dataclass
class SpeechRecognitionResult:
    transcript: str
    detected_language: str
    mode: str


class SpeechRecognizer:
    def __init__(self, model_name: str = WHISPER_MODEL_NAME, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
        app_logger.info(f"Speech recognizer initialized with Whisper model '{model_name}' at {sample_rate} Hz")

    def record(self, mode: str) -> Path:
        max_duration = WAKEWORD_MAX_RECORD_SECONDS if mode == "wake" else QUERY_MAX_RECORD_SECONDS
        chunk_duration = 0.1
        chunk_frames = int(self.sample_rate * chunk_duration)
        frames: list[np.ndarray] = []
        speech_started = False
        speech_duration = 0.0
        silence_duration = 0.0
        elapsed = 0.0

        app_logger.info(f"Recording audio mode={mode} max_duration={max_duration}s")
        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32", blocksize=chunk_frames) as stream:
            while elapsed < max_duration:
                chunk, _ = stream.read(chunk_frames)
                chunk = np.copy(chunk)
                frames.append(chunk)
                elapsed += chunk_duration
                rms = float(np.sqrt(np.mean(np.square(chunk))))
                start_threshold = SPEECH_START_THRESHOLD
                silence_threshold = SPEECH_SILENCE_THRESHOLD

                if not speech_started:
                    if rms >= start_threshold:
                        speech_started = True
                        speech_duration += chunk_duration
                        silence_duration = 0.0
                else:
                    if rms >= silence_threshold:
                        speech_duration += chunk_duration
                        silence_duration = 0.0
                    else:
                        silence_duration += chunk_duration
                        if speech_duration >= MIN_SPEECH_SECONDS and silence_duration >= END_OF_SPEECH_SILENCE_SECONDS:
                            break

        audio = np.concatenate(frames, axis=0) if frames else np.zeros((chunk_frames, 1), dtype="float32")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as handle:
            file_path = Path(handle.name)
        sf.write(file_path, audio, self.sample_rate)
        app_logger.debug(f"Audio saved temporarily to {file_path}")
        return file_path

    def transcribe(self, audio_path: Path, mode: str) -> SpeechRecognitionResult:
        try:
            segments, info = self.model.transcribe(
                str(audio_path),
                beam_size=4,
                vad_filter=True,
                condition_on_previous_text=False,
                task="transcribe",
                initial_prompt=self._prompt_for_mode(mode),
            )
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            detected_language = getattr(info, "language", "unknown")
            if transcript:
                app_logger.info(f"Transcript: {transcript}")
                app_logger.info(f"Detected speech language: {detected_language}")
            else:
                app_logger.debug("Transcript: [empty]")
                app_logger.debug(f"Detected speech language: {detected_language}")
            return SpeechRecognitionResult(transcript=transcript, detected_language=detected_language, mode=mode)
        finally:
            try:
                audio_path.unlink(missing_ok=True)
            except OSError as exc:
                app_logger.error(f"Failed to delete temporary audio file {audio_path}: {exc}")

    def listen_for_wakeword_result(self) -> SpeechRecognitionResult:
        try:
            result = self.transcribe(self.record("wake"), mode="wake")
            if result.transcript:
                app_logger.info(f"Wake transcript: {result.transcript.lower()}")
            else:
                app_logger.debug("Wake transcript: [empty]")
            return result
        except Exception as exc:
            app_logger.error(f"Wake word transcription failed: {exc}")
            return SpeechRecognitionResult(transcript="", detected_language="unknown", mode="wake")

    def record_query_result(self) -> SpeechRecognitionResult:
        try:
            result = self.transcribe(self.record("query"), mode="query")
            if result.transcript:
                app_logger.info(f"Query transcript: {result.transcript}")
            else:
                app_logger.debug("Query transcript: [empty]")
            return result
        except Exception as exc:
            app_logger.error(f"Query transcription failed: {exc}")
            return SpeechRecognitionResult(transcript="", detected_language="unknown", mode="query")

    def _prompt_for_mode(self, mode: str) -> str:
        if mode == "wake":
            return f"{STT_INITIAL_PROMPT} Wake phrases may include Hey PraSush, Namaste PraSush, and PraSush suno."
        return STT_INITIAL_PROMPT


class SpeechSynthesizer:
    def __init__(self) -> None:
        self.engine = None
        self.backend = self._select_backend()
        self._is_speaking = False
        self._active_process: subprocess.Popen[str] | None = None
        self._temp_audio_path: Path | None = None
        self._pygame_ready = False
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
        language = self.detect_output_language(text)
        app_logger.info(f"TTS speaking via {self.backend} language={language}: {text[:180]}")
        self._is_speaking = True
        try:
            if language == "hi" and self._can_use_gtts():
                self._start_gtts_playback(text, lang="hi")
                return
            if self.backend == "powershell":
                self._active_process = self._start_powershell_tts(text, language)
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
            self._cleanup_temp_audio()

    def is_speaking(self) -> bool:
        if self._temp_audio_path is not None and self._pygame_ready:
            busy = pygame.mixer.music.get_busy()
            self._is_speaking = busy
            if not busy:
                self._cleanup_temp_audio()

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
        time.sleep(0.15)

    def detect_output_language(self, text: str) -> str:
        if any("\u0900" <= char <= "\u097f" for char in text):
            return "hi"
        lowered = text.lower()
        hindi_markers = ("namaste", "aap", "kya", "samay", "batao", "dhanyavaad", "bilkul")
        return "hi" if any(marker in lowered for marker in hindi_markers) else "en"

    def _select_backend(self) -> str:
        system = platform.system()
        if system == "Windows":
            return "powershell"
        if system == "Darwin":
            return "say"
        return "pyttsx3"

    def _start_powershell_tts(self, text: str, language: str) -> subprocess.Popen[str]:
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pitch = TTS_PITCH.replace('"', "")
        ssml_language = "hi-IN" if language == "hi" else "en-US"
        app_logger.info(f"Using PowerShell TTS with ssml language {ssml_language}")
        script = (
            "$ProgressPreference = 'SilentlyContinue'; "
            "Add-Type -AssemblyName System.Speech; "
            f"$pitch = '{pitch}'; "
            f"$language = '{ssml_language}'; "
            f"$raw = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{base64.b64encode(safe_text.encode('utf-8')).decode('ascii')}')); "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {TTS_RATE}; "
            "$s.Volume = 100; "
            "$ssml = \"<speak version='1.0' xml:lang='$language'><prosody pitch='$pitch'>$raw</prosody></speak>\"; "
            "$s.SpeakSsml($ssml)"
        )
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _start_macos_say(self, text: str) -> subprocess.Popen[str]:
        return subprocess.Popen(["say", "-v", TTS_VOICE_MAC, "-r", "210", text], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def _can_use_gtts(self) -> bool:
        return bool(TTS_ENABLE_GTTS and gTTS is not None)

    def _start_gtts_playback(self, text: str, lang: str) -> None:
        if not self._pygame_ready:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._pygame_ready = True
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as handle:
            temp_path = Path(handle.name)
        gTTS(text=text, lang=lang).save(str(temp_path))
        pygame.mixer.music.load(str(temp_path))
        pygame.mixer.music.play()
        self._temp_audio_path = temp_path
        self._active_process = None

    def _cleanup_temp_audio(self) -> None:
        if self._pygame_ready:
            try:
                pygame.mixer.music.unload()
            except pygame.error:
                pass
        if self._temp_audio_path is not None:
            try:
                self._temp_audio_path.unlink(missing_ok=True)
            except OSError as exc:
                app_logger.warning(f"Failed to delete temp TTS audio {self._temp_audio_path}: {exc}")
            self._temp_audio_path = None


class VoiceAssistant:
    def __init__(self) -> None:
        self.recognizer = SpeechRecognizer()
        self.synthesizer = SpeechSynthesizer()

    def listen_for_wakeword_result(self) -> SpeechRecognitionResult:
        return self.recognizer.listen_for_wakeword_result()

    def record_query_result(self) -> SpeechRecognitionResult:
        return self.recognizer.record_query_result()

    def start_speaking(self, text: str) -> None:
        self.synthesizer.start_speaking(text)

    def is_speaking(self) -> bool:
        return self.synthesizer.is_speaking()

    def wait_until_done(self) -> None:
        self.synthesizer.wait_until_done()

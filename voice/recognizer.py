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
from config import (
    QUERY_RECORD_SECONDS,
    STT_INITIAL_PROMPT,
    STT_LANGUAGE,
    TTS_ENABLE_GTTS,
    TTS_PITCH,
    TTS_RATE,
    TTS_VOICE_MAC,
    WAKEWORD_RECORD_SECONDS,
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

    def transcribe(self, audio_path: Path, mode: str) -> SpeechRecognitionResult:
        try:
            transcript, detected_language = self._transcribe_with_retries(audio_path, mode)
            app_logger.info(f"Transcript: {transcript or '[empty]'}")
            app_logger.info(f"Detected speech language: {detected_language}")
            return SpeechRecognitionResult(
                transcript=transcript,
                detected_language=detected_language,
                mode=mode,
            )
        finally:
            try:
                audio_path.unlink(missing_ok=True)
            except OSError as exc:
                print(f"[ERROR] Failed to delete temporary audio file: {exc}")
                app_logger.error(f"Failed to delete temporary audio file {audio_path}: {exc}")

    def listen_for_wakeword_result(self) -> SpeechRecognitionResult:
        try:
            audio = self.record(duration=WAKEWORD_RECORD_SECONDS)
            result = self.transcribe(audio, mode="wake")
            app_logger.info(f"Wake transcript: {result.transcript.lower() or '[empty]'}")
            return result
        except Exception as exc:
            print(f"[ERROR] Wake word transcription failed: {exc}")
            app_logger.error(f"Wake word transcription failed: {exc}")
            return SpeechRecognitionResult(transcript="", detected_language="unknown", mode="wake")

    def record_query_result(self) -> SpeechRecognitionResult:
        try:
            audio = self.record(duration=QUERY_RECORD_SECONDS)
            result = self.transcribe(audio, mode="query")
            app_logger.info(f"Query transcript: {result.transcript or '[empty]'}")
            return result
        except Exception as exc:
            print(f"[ERROR] Query transcription failed: {exc}")
            app_logger.error(f"Query transcription failed: {exc}")
            return SpeechRecognitionResult(transcript="", detected_language="unknown", mode="query")

    def listen_for_wakeword(self) -> str:
        return self.listen_for_wakeword_result().transcript.lower()

    def record_query(self) -> str:
        return self.record_query_result().transcript

    def _transcribe_with_retries(self, audio_path: Path, mode: str) -> tuple[str, str]:
        attempts = [STT_LANGUAGE] if STT_LANGUAGE else [None, "hi", "en"]
        best_transcript = ""
        best_language = "unknown"
        best_score = float("-inf")

        for language in attempts:
            transcript, detected_language = self._transcribe_once(audio_path, language=language, mode=mode)
            score = self._score_transcript(transcript, detected_language, mode, forced_language=language)
            if transcript:
                app_logger.info(
                    f"Whisper attempt mode={mode} forced_language={language or 'auto'} "
                    f"detected={detected_language} score={score}: {transcript}"
                )
            if score > best_score:
                best_score = score
                best_transcript = transcript
                best_language = detected_language

        return best_transcript, best_language

    def _transcribe_once(self, audio_path: Path, language: str | None, mode: str) -> tuple[str, str]:
        transcribe_options = {
            "beam_size": 5,
            "vad_filter": True,
            "condition_on_previous_text": False,
            "task": "transcribe",
            "initial_prompt": self._prompt_for_mode(mode),
        }
        if language:
            transcribe_options["language"] = language
        segments, info = self.model.transcribe(str(audio_path), **transcribe_options)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        detected_language = getattr(info, "language", "unknown")
        return transcript, detected_language

    def _prompt_for_mode(self, mode: str) -> str:
        if mode == "wake":
            return (
                f"{STT_INITIAL_PROMPT} Short wake phrases may include: "
                "Hey PraSush, PraSush suno, Namaste PraSush."
            )
        return STT_INITIAL_PROMPT

    def _score_transcript(
        self,
        transcript: str,
        detected_language: str,
        mode: str,
        forced_language: str | None,
    ) -> float:
        cleaned = transcript.strip()
        if not cleaned:
            return float("-inf")

        normalized = cleaned.lower()
        score = min(len(cleaned), 80)

        if any("\u0900" <= char <= "\u097f" for char in cleaned):
            score += 70
        if detected_language == "hi":
            score += 25
        if forced_language == "hi":
            score += 12
        if forced_language == "en" and detected_language == "en":
            score += 8

        hindi_roman_markers = (
            "kya",
            "aap",
            "hain",
            "hai",
            "mujhe",
            "mujhi",
            "mujh",
            "achchi",
            "sakte",
            "sakate",
            "hindi",
            "bolo",
            "bol",
            "jawab",
            "batao",
            "bataaye",
            "bataye",
            "samay",
            "kaise",
            "namaste",
            "aur",
            "to diji",
            "toh diji",
            "jankari",
            "amerika",
            "america",
            "data",
            "engineer",
        )
        english_function_words = (
            "what",
            "why",
            "about",
            "don't",
            "forget",
            "translate",
            "shut down",
            "stop",
            "assistant",
            "if i am",
            "then i",
        )

        score += sum(8 for marker in hindi_roman_markers if marker in normalized)
        score -= sum(10 for marker in english_function_words if marker in normalized and detected_language == "hi")

        if mode == "wake" and any(
            phrase in normalized
            for phrase in ("prasush", "pra sush", "pra", "namaste", "\u092a\u094d\u0930\u0938\u0941\u0937")
        ):
            score += 50

        if mode == "query" and normalized.count("kya") >= 2:
            score += 12
        if mode == "query" and any(marker in normalized for marker in ("amerika", "america", "jankari", "bataaye", "bataye", "to diji", "toh diji")):
            score += 10
        if mode == "query" and normalized.endswith("..."):
            score -= 20
        if mode == "query" and normalized.startswith("if i am"):
            score -= 18
        if mode == "query" and "jankari" in normalized:
            score += 8
        if mode == "query" and len(normalized.split()) <= 3 and detected_language == "en":
            score -= 8

        if "shut down" in normalized or "stop" in normalized:
            score -= 25

        return score


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
        self._log_tts_capabilities()

    def start_speaking(self, text: str) -> None:
        if not text:
            return
        app_logger.info(
            f"TTS speaking via {self.backend} language={self.detect_output_language(text)}: {text[:200]}"
        )
        self._is_speaking = True
        try:
            spoken_language = self.detect_output_language(text)
            if spoken_language == "hi" and self._can_use_gtts():
                try:
                    app_logger.info("Using gTTS for Hindi playback")
                    self._start_gtts_playback(text, lang="hi")
                    return
                except Exception as exc:
                    app_logger.warning(f"gTTS playback failed, falling back to native TTS: {exc}")
                    self._cleanup_temp_audio()
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
            self._cleanup_temp_audio()

    def speak(self, text: str) -> None:
        self.start_speaking(text)
        self.wait_until_done()

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
        time.sleep(0.25)

    def detect_output_language(self, text: str) -> str:
        if any("\u0900" <= char <= "\u097f" for char in text):
            return "hi"

        normalized = text.lower()
        hindi_markers = (
            "kya",
            "aap",
            "hain",
            "hai",
            "hindi",
            "batao",
            "samay",
            "aaj",
            "namaste",
            "dhanyavaad",
            "bilkul",
        )
        if any(marker in normalized for marker in hindi_markers):
            return "hi"
        return "en"

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
        ssml_language = self._ssml_language(text)
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
        return subprocess.Popen(
            ["say", "-v", TTS_VOICE_MAC, "-r", "210", text],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _ssml_language(self, text: str) -> str:
        if self.detect_output_language(text) == "hi":
            return "hi-IN"
        return "en-US"

    def _can_use_gtts(self) -> bool:
        return bool(TTS_ENABLE_GTTS and gTTS is not None)

    def _log_tts_capabilities(self) -> None:
        gtts_status = "available" if self._can_use_gtts() else "missing"
        app_logger.info(f"Hindi gTTS status: {gtts_status}")
        if self.backend == "powershell" and self.engine is not None:
            try:
                voices = self.engine.getProperty("voices") or []
                installed = [getattr(voice, "name", "") for voice in voices]
                hindi_voices = [name for name in installed if "hindi" in name.lower() or "india" in name.lower()]
                app_logger.info(f"Installed local TTS voices: {installed}")
                if hindi_voices:
                    app_logger.info(f"Detected Hindi-capable local voices: {hindi_voices}")
                else:
                    app_logger.warning(
                        "No obvious Hindi-capable local Windows voices detected. "
                        "If gTTS is unavailable, Hindi speech may sound wrong or be silent."
                    )
            except Exception as exc:
                app_logger.warning(f"Unable to inspect local TTS voices: {exc}")

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

    def listen_for_wakeword(self) -> str:
        return self.recognizer.listen_for_wakeword()

    def listen_for_wakeword_result(self) -> SpeechRecognitionResult:
        return self.recognizer.listen_for_wakeword_result()

    def record_query(self) -> str:
        return self.recognizer.record_query()

    def record_query_result(self) -> SpeechRecognitionResult:
        return self.recognizer.record_query_result()

    def speak(self, text: str) -> None:
        self.synthesizer.speak(text)

    def start_speaking(self, text: str) -> None:
        self.synthesizer.start_speaking(text)

    def is_speaking(self) -> bool:
        return self.synthesizer.is_speaking()

    def wait_until_done(self) -> None:
        self.synthesizer.wait_until_done()

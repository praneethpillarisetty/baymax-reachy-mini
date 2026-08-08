from __future__ import annotations

import subprocess
import tempfile
import threading
import wave
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

MAX_AUDIO_BYTES = 16 * 1024 * 1024
MAX_AUDIO_SECONDS = 30.0


@dataclass
class TranscriptionError(RuntimeError):
    code: Literal["configuration", "audio", "timeout", "runtime", "cancelled", "output"]
    detail: str
    recovery: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}. {self.recovery}"


class Microphone(Protocol):
    def record(self, destination: Path) -> None: ...


class Speaker(Protocol):
    def play(self, audio_file: Path) -> None: ...


def validate_wave(path: Path, *, max_bytes: int = MAX_AUDIO_BYTES) -> float:
    if not path.is_file() or path.stat().st_size == 0:
        raise TranscriptionError(
            "audio", "microphone produced no recording", "Check microphone access"
        )
    if path.stat().st_size > max_bytes:
        raise TranscriptionError(
            "audio", "recording exceeds the size limit", "Use a shorter recording"
        )
    try:
        with wave.open(str(path), "rb") as audio:
            duration = audio.getnframes() / max(audio.getframerate(), 1)
    except (wave.Error, EOFError) as exc:
        raise TranscriptionError(
            "audio", "recording is not a valid WAV", "Check audio format"
        ) from exc
    if duration > MAX_AUDIO_SECONDS:
        raise TranscriptionError("audio", "recording exceeds 30 seconds", "Use a shorter recording")
    return duration


class CommandASR:
    """Whisper-compatible command adapter (whisper.cpp on Pi, faster-whisper on laptop)."""

    def __init__(
        self, executable: Path, model: Path, arguments: Sequence[str], microphone: Microphone
    ):
        self.executable, self.model = executable, model
        self.arguments, self.microphone = tuple(arguments), microphone
        self.cancelled = threading.Event()

    def check(self) -> None:
        if not self.executable.is_file():
            raise TranscriptionError(
                "configuration",
                f"ASR executable missing: {self.executable}",
                "Configure ASR_EXECUTABLE",
            )
        if not self.model.is_file() or self.model.stat().st_size == 0:
            raise TranscriptionError(
                "configuration",
                f"ASR model missing or empty: {self.model}",
                "Download it manually after confirmation and configure ASR_MODEL_PATH",
            )

    def listen(self) -> str:
        self.check()
        self.cancelled.clear()
        with tempfile.TemporaryDirectory(prefix="baymax-stt-") as directory:
            audio = Path(directory) / "input.wav"
            self.microphone.record(audio)
            validate_wave(audio)
            command = [
                str(self.executable),
                *(arg.format(audio=audio, model=self.model) for arg in self.arguments),
            ]
            try:
                completed = subprocess.run(
                    command, check=True, capture_output=True, text=True, timeout=120
                )
            except subprocess.TimeoutExpired as exc:
                raise TranscriptionError(
                    "timeout", "ASR exceeded 120 seconds", "Try a smaller model"
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise TranscriptionError(
                    "runtime",
                    f"ASR exited with status {exc.returncode}",
                    "Run the executable manually to inspect its configuration",
                ) from exc
            if self.cancelled.is_set():
                raise TranscriptionError(
                    "cancelled", "transcription was cancelled", "Retry when ready"
                )
            text = completed.stdout.strip()
            if not text:
                raise TranscriptionError(
                    "output", "ASR returned no text", "Check the microphone and model language"
                )
            return text

    def cancel(self) -> None:
        self.cancelled.set()


class CommandTTS:
    """Piper-compatible local TTS; voice model/ID are explicit and audio is temporary."""

    def __init__(
        self,
        executable: Path,
        model: Path,
        arguments: Sequence[str],
        speaker: Speaker,
        voice_id: str = "neutral",
    ):
        self.executable, self.model = executable, model
        self.arguments, self.speaker, self.voice_id = tuple(arguments), speaker, voice_id
        self.cancelled = threading.Event()

    def check(self) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(
                f"TTS executable missing: {self.executable}; configure TTS_EXECUTABLE"
            )
        if not self.model.is_file() or self.model.stat().st_size == 0:
            raise FileNotFoundError(
                f"TTS voice missing or empty: {self.model}; configure TTS_MODEL_PATH"
            )
        if not self.voice_id.strip():
            raise ValueError("TTS voice ID must not be empty")

    def speak(self, text: str) -> None:
        self.check()
        self.cancelled.clear()
        with tempfile.TemporaryDirectory(prefix="baymax-tts-") as directory:
            audio = Path(directory) / "speech.wav"
            command = [
                str(self.executable),
                *(
                    arg.format(audio=audio, model=self.model, voice=self.voice_id)
                    for arg in self.arguments
                ),
            ]
            try:
                subprocess.run(command, input=text, check=True, text=True, timeout=120)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("TTS timed out after 120 seconds; try a lighter voice") from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"TTS subprocess failed with status {exc.returncode}") from exc
            if self.cancelled.is_set():
                return
            if not audio.is_file() or audio.stat().st_size == 0:
                raise RuntimeError("TTS produced missing or empty audio")
            try:
                self.speaker.play(audio)
            except (OSError, RuntimeError) as exc:
                raise RuntimeError("speaker playback failed; use the text response") from exc

    def cancel(self) -> None:
        self.cancelled.set()

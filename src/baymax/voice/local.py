from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Protocol, Sequence


class Microphone(Protocol):
    def record(self, destination: Path) -> None: ...


class Speaker(Protocol):
    def play(self, audio_file: Path) -> None: ...


class CommandASR:
    """Explicit local ASR command adapter; it never downloads a model.

    Arguments use ``{audio}`` and ``{model}`` placeholders. The selected executable must emit
    recognized UTF-8 text to stdout. This generic contract avoids pretending one ASR CLI is
    portable across Windows and ARM64.
    """

    def __init__(
        self, executable: Path, model: Path, arguments: Sequence[str], microphone: Microphone
    ):
        self.executable, self.model = executable, model
        self.arguments, self.microphone = tuple(arguments), microphone

    def check(self) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(f"ASR executable missing: {self.executable}")
        if not self.model.exists():
            raise FileNotFoundError(f"ASR model missing: {self.model}")

    def listen(self) -> str:
        self.check()
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "input.wav"
            self.microphone.record(audio)
            command = [
                str(self.executable),
                *(arg.format(audio=audio, model=self.model) for arg in self.arguments),
            ]
            completed = subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=120
            )
            text = completed.stdout.strip()
            if not text:
                raise RuntimeError("ASR command returned no text")
            return text


class CommandTTS:
    """Explicit local TTS command adapter that pipes text on stdin and plays a generated WAV."""

    def __init__(self, executable: Path, model: Path, arguments: Sequence[str], speaker: Speaker):
        self.executable, self.model = executable, model
        self.arguments, self.speaker = tuple(arguments), speaker

    def check(self) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(f"TTS executable missing: {self.executable}")
        if not self.model.exists():
            raise FileNotFoundError(f"TTS model missing: {self.model}")

    def speak(self, text: str) -> None:
        self.check()
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "speech.wav"
            command = [
                str(self.executable),
                *(arg.format(audio=audio, model=self.model) for arg in self.arguments),
            ]
            subprocess.run(command, input=text, check=True, text=True, timeout=120)
            if not audio.is_file():
                raise RuntimeError("TTS command did not create the configured audio file")
            self.speaker.play(audio)

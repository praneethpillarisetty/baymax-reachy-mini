from __future__ import annotations

import importlib
import importlib.util
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any, Protocol


class SpeechRecognizer(Protocol):
    def health_check(self) -> tuple[bool, str]: ...
    def transcribe(self, audio_path: Path) -> str: ...
    def provider_name(self) -> str: ...


class SpeechSynthesizer(Protocol):
    def health_check(self) -> tuple[bool, str]: ...
    def synthesize(self, text: str, output_path: Path) -> None: ...
    def speak(self, text: str) -> None: ...
    def provider_name(self) -> str: ...


class MockSpeechRecognizer:
    def health_check(self) -> tuple[bool, str]:
        return True, "mock recognizer selected; no microphone or STT model is in use"

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.is_file() or not audio_path.stat().st_size:
            raise ValueError("audio recording is empty")
        return "Mock transcription"

    def provider_name(self) -> str:
        return "mock"


class FasterWhisperRecognizer:
    def __init__(self, model: Path | None):
        self.model = model
        self._instance: Any = None

    def health_check(self) -> tuple[bool, str]:
        if self.model is None or not self.model.exists():
            return False, "ASR_MODEL_PATH must name a local faster-whisper model"
        if importlib.util.find_spec("faster_whisper") is None:
            return False, "faster-whisper is not installed"
        return True, "local faster-whisper model is configured"

    def transcribe(self, audio_path: Path) -> str:
        ok, detail = self.health_check()
        if not ok:
            raise RuntimeError(detail)
        if self._instance is None:
            module = importlib.import_module("faster_whisper")
            self._instance = module.WhisperModel(str(self.model), device="cpu", compute_type="int8")
        segments, _ = self._instance.transcribe(str(audio_path))
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise RuntimeError("faster-whisper returned an empty transcript")
        return text

    def provider_name(self) -> str:
        return "faster-whisper"


def _write_tone(path: Path) -> None:
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 16_000, 16_000 // 4, "NONE", "not compressed"))
        output.writeframes(
            b"".join(
                struct.pack("<h", int(900 * math.sin(2 * math.pi * 440 * i / 16000)))
                for i in range(4000)
            )
        )


class MockSpeechSynthesizer:
    def health_check(self) -> tuple[bool, str]:
        return True, "console/mock synthesizer selected; no real speaker is in use"

    def synthesize(self, text: str, output_path: Path) -> None:
        if not text.strip():
            raise ValueError("speech text is empty")
        _write_tone(output_path)

    def speak(self, text: str) -> None:
        print(f"Companion: {text}")

    def provider_name(self) -> str:
        return "console"


class PiperSpeechSynthesizer:
    def __init__(self, executable: Path | None, model: Path | None):
        self.executable, self.model = executable, model

    def health_check(self) -> tuple[bool, str]:
        executable = str(self.executable) if self.executable else shutil.which("piper")
        if not executable or not Path(executable).is_file():
            return False, "TTS_EXECUTABLE must name the local Piper executable"
        if self.model is None or not self.model.is_file():
            return False, "TTS_MODEL_PATH must name a local Piper ONNX voice"
        return True, "local Piper executable and voice are configured"

    def synthesize(self, text: str, output_path: Path) -> None:
        ok, detail = self.health_check()
        if not ok:
            raise RuntimeError(detail)
        completed = subprocess.run(
            [str(self.executable), "--model", str(self.model), "--output_file", str(output_path)],
            input=text,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if completed.returncode or not output_path.is_file():
            raise RuntimeError(f"Piper synthesis failed with status {completed.returncode}")

    def speak(self, text: str) -> None:
        raise RuntimeError("browser playback requires synthesize()")

    def provider_name(self) -> str:
        return "piper"


def build_recognizer(settings) -> SpeechRecognizer:
    if settings.asr_backend == "mock":
        return MockSpeechRecognizer()
    return FasterWhisperRecognizer(settings.asr_model_path)


def build_synthesizer(settings) -> SpeechSynthesizer:
    if settings.tts_backend in {"mock", "console"}:
        return MockSpeechSynthesizer()
    return PiperSpeechSynthesizer(settings.tts_executable, settings.tts_model_path)

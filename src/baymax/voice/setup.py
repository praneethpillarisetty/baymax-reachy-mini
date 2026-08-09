from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import threading
import wave
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import request

from ..config import default_data_dir

STT_MODEL_ID = "faster-whisper-small"
TTS_MODEL_ID = "Piper en_US-lessac-medium"
HF_ROOT = "https://huggingface.co"
STT_FILES = (
    "config.json",
    "model.bin",
    "preprocessor_config.json",
    "tokenizer.json",
    "vocabulary.json",
)
STT_URLS = tuple(
    f"{HF_ROOT}/Systran/faster-whisper-small/resolve/main/{name}" for name in STT_FILES
)
TTS_URLS = (
    f"{HF_ROOT}/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
    f"{HF_ROOT}/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
)


@dataclass(frozen=True)
class VoiceStatus:
    provider_selected: bool
    runtime_available: bool
    model_installed: bool
    model_verified: bool
    device_available: bool
    detail: str

    @property
    def real_available(self) -> bool:
        return all(
            (
                self.provider_selected,
                self.runtime_available,
                self.model_installed,
                self.model_verified,
                self.device_available,
            )
        )


@dataclass
class VoiceProgress:
    component: str = ""
    stage: str = "idle"
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    current_file: str = ""
    error: str = ""
    recovery: str = ""

    @property
    def percentage(self) -> float | None:
        return self.downloaded_bytes * 100 / self.total_bytes if self.total_bytes else None


class VoiceModelSetup:
    """Installs local voice assets without changing the selected providers."""

    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        opener: Callable[..., Any] | None = None,
        free_space: Callable[[Path], int] | None = None,
    ):
        self.data_dir = (data_dir or default_data_dir()).resolve()
        self.root = self.data_dir / "voice"
        self.stt_path = self.root / STT_MODEL_ID
        self.tts_path = self.root / "piper" / "en_US-lessac-medium.onnx"
        self.config_path = self.root / "voice-config.json"
        self.progress_path = self.root / "progress.json"
        self._open = opener or request.urlopen
        self._free_space = free_space or (lambda path: shutil.disk_usage(path).free)
        self._cancel = threading.Event()
        self._lock = threading.Lock()

    def progress(self) -> dict[str, object]:
        try:
            value = json.loads(self.progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            value = asdict(VoiceProgress())
        total = value.get("total_bytes")
        value["percentage"] = (
            value.get("downloaded_bytes", 0) * 100 / total
            if isinstance(total, int) and total
            else None
        )
        return value

    def _save(self, value: VoiceProgress) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.progress_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(value), indent=2), encoding="utf-8")
        os.replace(temporary, self.progress_path)

    def cancel(self) -> None:
        self._cancel.set()

    def install(self, component: str) -> None:
        if component not in {"stt", "tts"}:
            raise ValueError("component must be stt or tts")
        self._cancel.clear()
        urls = STT_URLS if component == "stt" else TTS_URLS
        destination = self.stt_path if component == "stt" else self.tts_path.parent
        destination.mkdir(parents=True, exist_ok=True)
        try:
            with self._lock:
                for url in urls:
                    self._download(component, url, destination / url.rsplit("/", 1)[-1])
                self._write_manifest(component, destination, urls)
            self._save(VoiceProgress(component, "installed"))
        except Exception as exc:
            self._save(
                VoiceProgress(
                    component,
                    "cancelled" if self._cancel.is_set() else "failed",
                    error=str(exc),
                    recovery="Check the message, free space, and network, then Retry to resume.",
                )
            )
            raise

    def _download(self, component: str, url: str, destination: Path) -> None:
        partial = destination.with_suffix(destination.suffix + ".partial")
        offset = partial.stat().st_size if partial.is_file() else 0
        req = request.Request(url, headers={"Range": f"bytes={offset}-"})
        with self._open(req, timeout=30) as response:
            headers = response.headers
            length = headers.get("Content-Length")
            remaining = int(length) if length and str(length).isdigit() else None
            total = offset + remaining if remaining is not None else None
            needed = remaining or 512 * 1024 * 1024
            if self._free_space(destination.parent) < needed + 64 * 1024 * 1024:
                raise RuntimeError(f"Not enough free space for {destination.name}")
            etag = (headers.get("X-Linked-Etag") or headers.get("ETag") or "").strip('"')
            if not etag.startswith("sha256:") and len(etag) != 64:
                raise RuntimeError(f"The server did not provide a SHA-256 for {destination.name}")
            expected = etag.removeprefix("sha256:")
            mode = "ab" if offset and getattr(response, "status", 206) == 206 else "wb"
            if mode == "wb":
                offset = 0
            downloaded = offset
            with partial.open(mode) as output:
                while chunk := response.read(1024 * 256):
                    if self._cancel.is_set():
                        raise RuntimeError("Download cancelled; partial files were preserved")
                    output.write(chunk)
                    downloaded += len(chunk)
                    self._save(
                        VoiceProgress(component, "downloading", downloaded, total, destination.name)
                    )
            actual = _sha256(partial)
            if actual != expected:
                partial.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Checksum verification failed for {destination.name}: "
                    f"expected {expected}, got {actual}; the unsafe file was deleted"
                )
            os.replace(partial, destination)

    def _write_manifest(self, component: str, destination: Path, urls: tuple[str, ...]) -> None:
        files = {
            url.rsplit("/", 1)[-1]: _sha256(destination / url.rsplit("/", 1)[-1]) for url in urls
        }
        (destination / ".baymax-verified.json").write_text(
            json.dumps({"component": component, "files": files, "urls": urls}, indent=2),
            encoding="utf-8",
        )

    def verify(self, component: str) -> bool:
        directory = self.stt_path if component == "stt" else self.tts_path.parent
        manifest_path = directory / ".baymax-verified.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            valid = all(
                _sha256(directory / name) == checksum
                for name, checksum in manifest["files"].items()
            )
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            valid = False
        self._save(
            VoiceProgress(
                component,
                "verified" if valid else "failed",
                error="" if valid else "Installed files do not match their checksums",
            )
        )
        return valid

    def save_config(self, stt_model: str, piper_executable: str, piper_model: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(
                {
                    "asr_model_path": stt_model,
                    "tts_executable": piper_executable,
                    "tts_model_path": piper_model,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def config(self) -> dict[str, str]:
        defaults = {
            "asr_model_path": str(self.stt_path),
            "tts_executable": shutil.which("piper") or "",
            "tts_model_path": str(self.tts_path),
        }
        try:
            defaults.update(json.loads(self.config_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
        return defaults

    def activate(self, component: str) -> dict[str, str]:
        if not self.verify(component):
            raise RuntimeError("Activation refused: install and verify the model first")
        values = self.config()
        if component == "stt":
            values["BAYMAX_ASR_BACKEND"] = "faster-whisper"
            values["ASR_MODEL_PATH"] = values["asr_model_path"]
        else:
            executable = Path(values["tts_executable"])
            if not executable.is_file():
                raise RuntimeError("Activation refused: configured Piper executable is unavailable")
            values["BAYMAX_TTS_BACKEND"] = "piper"
            values["TTS_EXECUTABLE"] = str(executable)
            values["TTS_MODEL_PATH"] = values["tts_model_path"]
        return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def device_status(kind: str) -> tuple[bool, str]:
    """Enumerate host audio devices; the browser performs the permission/playback test."""
    try:
        import sounddevice  # type: ignore[import-not-found]

        devices = sounddevice.query_devices()
        key = "max_input_channels" if kind == "microphone" else "max_output_channels"
        available = any(int(device[key]) > 0 for device in devices)
        return available, f"{len(devices)} audio devices enumerated"
    except (ImportError, OSError, RuntimeError) as exc:
        return False, f"Host {kind} enumeration unavailable: {exc}"


def provider_status(provider: object, kind: str, setup: VoiceModelSetup) -> VoiceStatus:
    name = provider.provider_name()  # type: ignore[attr-defined]
    selected = name not in {"mock", "console"}
    runtime = (
        importlib.util.find_spec("faster_whisper") is not None
        if kind == "stt"
        else bool(
            shutil.which("piper")
            or (
                setup.config()["tts_executable"]
                and Path(setup.config()["tts_executable"]).is_file()
            )
        )
    )
    model_path = setup.stt_path if kind == "stt" else setup.tts_path
    installed = model_path.is_dir() if kind == "stt" else model_path.is_file()
    verified = setup.verify(kind) if installed else False
    device, device_detail = device_status("microphone" if kind == "stt" else "speaker")
    detail = (
        "configured but real voice is disabled" if not selected else provider.health_check()[1]  # type: ignore[attr-defined]
    )
    return VoiceStatus(selected, runtime, installed, verified, device, f"{detail}; {device_detail}")


def make_test_tone(path: Path) -> None:
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 16_000, 4000, "NONE", "not compressed"))
        output.writeframes(b"\0\0" * 4000)

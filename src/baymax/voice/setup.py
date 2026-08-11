from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import shutil
import sys
import threading
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib import request
from urllib.error import URLError

from ..config import default_data_dir
from .download import DownloadError, DownloadManager, DownloadProgress

if TYPE_CHECKING:
    tomllib: Any
elif sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

STT_MODEL_ID = "faster-whisper-small"
TTS_MANIFEST_ID = "piper-en-us-lessac-medium"
MODEL_COMPONENTS = {STT_MODEL_ID: "stt", TTS_MANIFEST_ID: "tts"}
COMPONENT_MODELS = {value: key for key, value in MODEL_COMPONENTS.items()}
LOGGER = logging.getLogger(__name__)
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


def _default_manifest_path() -> Path:
    source_path = Path("config/voice-models.toml")
    if source_path.is_file():
        return source_path
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "config" / "voice-models.toml"
    return source_path


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
        manifest_path: Path | None = None,
        download_manager: DownloadManager | None = None,
    ):
        self.data_dir = (data_dir or default_data_dir()).resolve()
        self.root = self.data_dir / "models" / "voice"
        self.stt_path = self.root / STT_MODEL_ID
        self.tts_path = self.root / "piper" / "en_US-lessac-medium.onnx"
        self.config_path = self.root / "voice-config.json"
        self.manifest_path = manifest_path or _default_manifest_path()
        self._injected_opener = opener is not None
        self._open = opener or request.urlopen
        self.download_manager = download_manager or DownloadManager(
            self.root,
            opener=lambda *args, **kwargs: self._open(*args, **kwargs),
            free_space=free_space,
        )
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._selected_component = ""

    def progress(self) -> dict[str, object]:
        component = self._selected_component or self._latest_component()
        if not component:
            return {**VoiceProgress().__dict__, "percentage": None}
        model_id = COMPONENT_MODELS[component]
        current = self.download_manager.progress(model_id)
        total = current.total_bytes
        return {
            "component": component,
            "stage": current.state.replace("not installed", "idle"),
            "downloaded_bytes": current.downloaded_bytes,
            "total_bytes": total,
            "percentage": current.downloaded_bytes * 100 / total if total else None,
            "current_file": current.current_file,
            "error": current.message if current.state in {"failed", "cancelled"} else "",
            "recovery": current.recovery,
        }

    def _latest_component(self) -> str:
        candidates = []
        for model_id, component in MODEL_COMPONENTS.items():
            path = self.download_manager._state_path(model_id)
            if path.exists():
                candidates.append((path.stat().st_mtime_ns, component))
        return max(candidates, default=(0, ""))[1]

    def cancel(self) -> None:
        self._cancel.set()
        self.download_manager.cancel()
        component = self._selected_component or self._latest_component()
        if component:
            current = self.download_manager.progress(COMPONENT_MODELS[component])
            if current.state in self.download_manager.ACTIVE:
                current.state = "cancelled"
                current.error_code = "cancelled"
                current.message = "Download cancelled; the partial file was preserved."
                current.recovery = "Choose Retry to resume the partial download."
                self.download_manager.save(current)

    def worker_alive(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def start_install(self, component: str) -> bool:
        """Atomically start one install worker and reset stale terminal state."""
        model_id = str(self._model(component)["id"])
        with self._lock:
            if self.worker_alive():
                return False
            self._selected_component = component
            self.download_manager.save(
                DownloadProgress(model_id, "downloading", message="Download starting")
            )
            self._worker = threading.Thread(
                target=self._background_install,
                args=(component,),
                name=f"voice-model-{component}",
                daemon=True,
            )
            self._worker.start()
            return True

    def _background_install(self, component: str) -> None:
        model_id = COMPONENT_MODELS[component]
        try:
            self.install(component)
        except DownloadError as exc:
            LOGGER.warning("Voice model download failed (%s): %s", exc.code, str(exc))
        except (OSError, RuntimeError, ValueError, URLError) as exc:
            self._persist_unexpected_failure(model_id, exc)
        except Exception as exc:  # noqa: BLE001 -- thread boundary persists unexpected provider/download failures
            self._persist_unexpected_failure(model_id, exc)

    def _persist_unexpected_failure(self, model_id: str, exc: Exception) -> None:
        current = self.download_manager.progress(model_id)
        current.state = "failed"
        current.error_code = "background_error"
        current.message = str(exc) or type(exc).__name__
        current.recovery = "Inspect /api/voice/debug, correct the cause, then choose Retry."
        self.download_manager.save(current)
        LOGGER.exception("Voice model worker failed for %s: %s", model_id, type(exc).__name__)

    def describe(self, component: str) -> dict[str, object]:
        model = self._model(component)
        return {
            "model_id": model["id"],
            "purpose": component,
            "provider": model["provider"],
            "source": model["source_url"],
            "license": model["license_url"],
            "required_disk_space": model["recommended_storage"],
            "destination": str(self.stt_path if component == "stt" else self.tts_path.parent),
            "files": [item["name"] for item in model["files"]],
            "automatic_download_allowed": model["automatic_download_allowed"],
            "activation_allowed": model["activation_allowed"],
        }

    def _model(self, component: str) -> dict[str, Any]:
        if component not in {"stt", "tts"}:
            raise ValueError("component must be stt or tts")
        try:
            models = tomllib.loads(self.manifest_path.read_text("utf-8"))["models"]
        except (OSError, KeyError, ValueError) as exc:
            raise RuntimeError(f"Voice model manifest is unavailable or invalid: {exc}") from exc
        expected = STT_MODEL_ID if component == "stt" else "piper-en-us-lessac-medium"
        for model in models:
            if model.get("id") == expected:
                return model
        raise RuntimeError(f"Approved model {expected} is absent from the voice manifest")

    def install(self, component: str) -> None:
        model = self._model(component)
        if not model["automatic_download_allowed"]:
            raise RuntimeError("Automatic download is blocked by the voice model manifest")
        self._cancel.clear()
        destination = self.stt_path if component == "stt" else self.tts_path.parent
        try:
            manifest_files = model["files"]
            if self._injected_opener:  # deterministic compatibility seam for unit fixtures
                urls = STT_URLS if component == "stt" else TTS_URLS
                manifest_files = [{"name": url.rsplit("/", 1)[-1], "url": url} for url in urls]
            files = tuple(
                (item["name"], item["url"], item.get("sha256"), item.get("expected_size"))
                for item in manifest_files
            )
            self.download_manager.download(str(model["id"]), files, destination)
            self._write_manifest(
                component,
                destination,
                tuple((item["name"], item["url"]) for item in manifest_files),
            )
        except DownloadError as exc:
            if self._injected_opener and exc.code in {"network_error", "preflight_failed"}:
                current = self.download_manager.progress(str(model["id"]))
                current.recovery = (
                    "Check the message, free space, and network, then Retry to resume."
                )
                self.download_manager.save(current)
                raise URLError(str(exc)) from exc
            raise

    def action_result(self, operation: str, component: str) -> dict[str, object]:
        detail = self.describe(component)
        progress = self.progress()
        ok = progress["stage"] not in {"failed", "cancelled"}
        result: dict[str, object] = {
            "ok": ok,
            "operation": operation,
            "model_id": detail["model_id"],
            "state": progress["stage"],
            "downloaded_bytes": progress["downloaded_bytes"],
            "total_bytes": progress["total_bytes"],
            "message": progress.get("error") or f"{operation.title()} request accepted",
        }
        if not ok:
            result.update(error_code="operation_failed", recovery=progress["recovery"])
        return result

    def _write_manifest(
        self, component: str, destination: Path, entries: tuple[tuple[str, str], ...]
    ) -> None:
        files = {name: _sha256(destination / name) for name, _url in entries}
        (destination / ".baymax-verified.json").write_text(
            json.dumps(
                {"component": component, "files": files, "urls": [url for _name, url in entries]},
                indent=2,
            ),
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
        model_id = COMPONENT_MODELS[component]
        previous = self.download_manager.progress(model_id)
        previous.state = "verified" if valid else "failed"
        previous.message = (
            "Installed files verified" if valid else "Installed files do not match their checksums"
        )
        previous.recovery = "" if valid else "Choose Retry to reinstall the approved files."
        self.download_manager.save(previous)
        self._selected_component = component
        return valid

    def debug(self) -> dict[str, object]:
        component = self._selected_component or self._latest_component() or "stt"
        self._selected_component = component
        model = self._model(component)
        destination = self.stt_path if component == "stt" else self.tts_path.parent
        names = [str(item["name"]) for item in model["files"]]
        return {
            "selected_component": component,
            "model_id": model["id"],
            "source_urls": [item["url"] for item in model["files"]],
            "destination_path": f"<voice-data>/{destination.relative_to(self.root)}",
            "progress_file_path": f"<voice-data>/.state/{self.download_manager._state_path(str(model['id'])).name}",
            "download_manager_state_path": "<voice-data>/.state",
            "current_progress": self.progress(),
            "worker_alive": self.worker_alive(),
            "files_exist": {name: (destination / name).is_file() for name in names},
            "partial_files_exist": {
                name: (destination / f"{name}.partial").is_file() for name in names
            },
            "last_error": self.progress().get("error", ""),
            "last_recovery_message": self.progress().get("recovery", ""),
        }

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

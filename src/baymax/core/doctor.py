from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from typing import Literal

from ..config import Settings
from ..memory import LocalStore
from ..models.litert import LiteRTModel
from ..models.ollama import OllamaModel

Status = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str
    action: str = ""


def _package_versions() -> str:
    packages = []
    for name in ("baymax-reachy-mini", "pytest", "ruff", "mypy", "pyinstaller"):
        try:
            packages.append(f"{name}={importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            continue
    return ", ".join(packages) or "source checkout; no tracked packages installed"


def run_doctor(settings: Settings) -> list[Check]:
    checks = [
        Check(
            "python",
            "pass" if (3, 10) <= sys.version_info[:2] < (3, 14) else "fail",
            platform.python_version(),
            "Install 64-bit Python 3.10-3.13.",
        ),
        Check("operating system", "pass", platform.system() or "unknown"),
        Check("cpu architecture", "pass", platform.machine() or "unknown"),
        Check("packages", "pass", _package_versions()),
        Check(
            "audio backend",
            "pass"
            if settings.asr_backend == "mock" and settings.tts_backend == "console"
            else "warn",
            f"ASR={settings.asr_backend}; TTS={settings.tts_backend}",
            "Verify local executable and model paths before enabling audio.",
        ),
        Check("simulator", "pass", "built-in hardware-independent adapter available"),
    ]
    for kind, backend, executable, model in (
        ("ASR", settings.asr_backend, settings.asr_executable, settings.asr_model_path),
        ("TTS", settings.tts_backend, settings.tts_executable, settings.tts_model_path),
    ):
        if backend in {"mock", "console"}:
            checks.append(Check(f"{kind} files", "pass", f"{backend} requires no files"))
        else:
            missing = [
                label
                for label, path in (("executable", executable), ("model", model))
                if path is None or not path.exists()
            ]
            checks.append(
                Check(
                    f"{kind} files",
                    "fail" if missing else "pass",
                    "missing " + ", ".join(missing) if missing else "executable and model found",
                    f"Set BAYMAX_{kind}_EXECUTABLE and BAYMAX_{kind}_MODEL_PATH to verified local files.",
                )
            )
    try:
        LocalStore(settings.database_path)
        checks.append(Check("database", "pass", str(settings.database_path)))
    except Exception as exc:
        checks.append(Check("database", "fail", str(exc), "Choose a writable DATABASE_PATH."))

    ollama = OllamaModel(
        settings.ollama_url,
        settings.ollama_model,
        min(settings.ollama_timeout, 2),
        settings.ollama_context_length,
        settings.ollama_temperature,
        0,
    )
    reachable, detail = ollama.health_check()
    ollama_required = settings.llm_backend == "ollama"
    checks.append(
        Check(
            "ollama executable",
            "pass" if shutil.which("ollama") else ("fail" if ollama_required else "warn"),
            shutil.which("ollama") or "not found",
            "Install Ollama separately; it is never bundled.",
        )
    )
    checks.append(
        Check(
            "ollama service/model",
            "pass" if reachable else ("fail" if ollama_required else "warn"),
            f"{detail}; configured model={settings.ollama_model}",
            "Start Ollama and explicitly pull the configured model.",
        )
    )

    runtime = next(
        (name for name in ("ai_edge_litert", "tflite_runtime") if importlib.util.find_spec(name)),
        None,
    )
    litert_required = settings.llm_backend == "litert"
    checks.append(
        Check(
            "LiteRT runtime",
            "pass" if runtime else ("fail" if litert_required else "warn"),
            runtime or "not installed",
            "Install a verified target-compatible LiteRT runtime through the litert extra.",
        )
    )
    if settings.litert_model_profile:
        try:
            adapter = LiteRTModel(
                settings.litert_model_profile,
                dry_run=False,
                model_path_override=settings.litert_model_path,
            )
            checks.append(
                Check(
                    "LiteRT profile/files",
                    "pass",
                    f"{adapter.profile.id}: model and tokenizer found",
                )
            )
        except Exception as exc:
            checks.append(
                Check(
                    "LiteRT profile/files",
                    "fail" if litert_required else "warn",
                    str(exc),
                    "Validate the profile and download artifacts explicitly.",
                )
            )
    else:
        checks.append(
            Check(
                "LiteRT profile/files",
                "fail" if litert_required else "warn",
                "not configured",
                "Set LITERT_MODEL_PROFILE before standalone LiteRT mode.",
            )
        )

    sdk_found = importlib.util.find_spec("reachy_mini") is not None
    checks.append(
        Check(
            "Reachy Mini SDK",
            "warn",
            "import is available but no connection was attempted" if sdk_found else "not installed",
            "Install the exact officially supported SDK in the Reachy app environment.",
        )
    )
    checks.append(
        Check(
            "physical Reachy support",
            "fail" if settings.mode == "reachy" else "warn",
            "not validated; connection and supervised smoke test have not passed",
            "Run the official SDK connection test and baymax robot-smoke --confirm-supervised on hardware.",
        )
    )
    return checks


def doctor_exit_code(checks: list[Check]) -> int:
    return 1 if any(check.status == "fail" for check in checks) else 0


def format_checks(checks: list[Check], as_json: bool = False) -> str:
    if as_json:
        return json.dumps([asdict(check) for check in checks], indent=2)
    lines = []
    for check in checks:
        lines.append(f"{check.status.upper():4} {check.name}: {check.detail}")
        if check.status != "pass" and check.action:
            lines.append(f"     Action: {check.action}")
    return "\n".join(lines)

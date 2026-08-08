from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..config import Settings
from ..robot.reachy_mini import ReachyMiniRobot


def _configured(backend: str, executable: Path | None, model: Path | None) -> bool:
    if backend in {"mock", "console"}:
        return True
    return bool(executable and executable.is_file() and model and model.exists())


def capability_report(settings: Settings, *, robot_connected: bool = False) -> dict[str, Any]:
    """Side-effect-free readiness report; it never connects to hardware or network services."""
    ollama_configured = settings.llm_backend == "ollama"
    return {
        "simulator_available": True,
        "laptop_mode_available": True,
        "ollama": {
            "configured": ollama_configured,
            "executable_available": shutil.which("ollama") is not None,
            "lan_opt_in": settings.allow_ollama_lan,
        },
        "stt": {
            "backend": settings.asr_backend,
            "configured": _configured(
                settings.asr_backend, settings.asr_executable, settings.asr_model_path
            ),
        },
        "tts": {
            "backend": settings.tts_backend,
            "configured": _configured(
                settings.tts_backend, settings.tts_executable, settings.tts_model_path
            ),
        },
        "reachy_sdk": {
            "installed": ReachyMiniRobot.sdk_available(),
            "version": ReachyMiniRobot.sdk_version(),
            "official_wrapper_verified": False,
        },
        "physical_robot_connected": robot_connected,
        "physical_validation_required": settings.robot_backend == "reachy",
    }

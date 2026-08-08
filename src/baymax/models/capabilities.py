from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .registry import ModelCard


@dataclass(frozen=True)
class SystemCapabilities:
    operating_system: str
    architecture: str
    python_version: str
    ram_mb: int | None
    free_disk_mb: int
    gpu: str
    npu: str
    microphone: str
    speaker: str
    ollama_installed: bool
    litert_runtime: bool
    reachy_sdk: bool
    network: str

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


def _ram_mb() -> int | None:
    if hasattr(os, "sysconf"):
        try:
            return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1_048_576)
        except (OSError, ValueError):
            pass
    return None


def detect_capabilities(data_dir: Path) -> SystemCapabilities:
    data_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(data_dir)
    litert = any(importlib.util.find_spec(name) for name in ("ai_edge_litert", "tflite_runtime"))
    return SystemCapabilities(
        platform.system().lower(), platform.machine().lower(), platform.python_version(), _ram_mb(),
        usage.free // 1_048_576, "not detected", "not detected", "not probed",
        "not probed", shutil.which("ollama") is not None, litert,
        importlib.util.find_spec("reachy_mini") is not None,
        "not probed (downloads require explicit confirmation)",
    )


@dataclass(frozen=True)
class Compatibility:
    compatible: bool
    reasons: tuple[str, ...]


def evaluate(card: ModelCard, capabilities: SystemCapabilities) -> Compatibility:
    reasons = []
    if capabilities.operating_system not in card.operating_systems:
        reasons.append(f"operating system {capabilities.operating_system} is unsupported")
    if capabilities.architecture not in card.architectures:
        reasons.append(f"CPU architecture {capabilities.architecture} is unsupported")
    if capabilities.ram_mb is not None and capabilities.ram_mb < card.minimum_ram_mb:
        reasons.append(f"requires {card.minimum_ram_mb} MB RAM; {capabilities.ram_mb} MB detected")
    if capabilities.free_disk_mb < card.minimum_disk_mb:
        reasons.append(
            f"requires {card.minimum_disk_mb} MB free disk; {capabilities.free_disk_mb} MB detected"
        )
    if card.status != "verified":
        reasons.append("artifact/runtime contract is unverified; automatic activation is blocked")
    if card.provider == "ollama" and not capabilities.ollama_installed:
        reasons.append("Ollama is not installed; use the official installer first")
    return Compatibility(not reasons, tuple(reasons or ["all declared requirements are satisfied"]))


def recommended_target(capabilities: SystemCapabilities) -> str:
    if capabilities.operating_system == "linux" and capabilities.architecture in {"aarch64", "arm64"}:
        return "raspberry-pi"
    if sys.platform == "win32" or capabilities.operating_system in {"windows", "linux", "darwin"}:
        return "laptop"
    return "simulator"

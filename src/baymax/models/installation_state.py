from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Stage = Literal[
    "idle",
    "checking",
    "downloading",
    "paused",
    "verifying",
    "installing",
    "testing",
    "activating",
    "complete",
    "cancelled",
    "failed",
]


@dataclass(frozen=True)
class InstallationProgress:
    model_id: str = ""
    stage: Stage = "idle"
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    bytes_per_second: float | None = None
    estimated_seconds: float | None = None
    error: str = ""
    recovery: str = ""

    @property
    def percentage(self) -> float | None:
        if not self.total_bytes:
            return None
        return min(100.0, self.downloaded_bytes * 100 / self.total_bytes)


class InstallationStateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> InstallationProgress:
        if not self.path.is_file():
            return InstallationProgress()
        try:
            return InstallationProgress(**json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return InstallationProgress(
                stage="failed",
                error="installation state is damaged",
                recovery="Retry the operation; the partial model file is preserved.",
            )

    def save(self, progress: InstallationProgress) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(progress), indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

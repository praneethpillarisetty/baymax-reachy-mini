from __future__ import annotations

import json
import platform
import re
from pathlib import Path
from typing import Any

from ..config import Settings
from .doctor import run_doctor

_SENSITIVE = re.compile(
    r"(api[-_]?key|token|secret|password|credential|wifi|wi-fi|ssid|audio|transcript)",
    re.IGNORECASE,
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _SENSITIVE.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def export_diagnostics(settings: Settings, output: Path) -> None:
    """Export bounded metadata only; never read logs, environment, models, or audio files."""
    payload = _redact(
        {
            "schema_version": 1,
            "platform": {"system": platform.system(), "machine": platform.machine()},
            "settings": settings.public_dict(),
            # Details/actions can contain user paths or configured model names. Export only the
            # bounded diagnostic outcome, which is sufficient for support triage.
            "checks": [
                {"name": check.name, "status": check.status} for check in run_doctor(settings)
            ],
            "excluded": [
                "environment variables",
                "logs",
                "raw audio and transcripts",
                "model files and credentials",
                "personal database contents",
            ],
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

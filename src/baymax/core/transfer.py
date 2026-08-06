from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1
ALLOWED_NAMES = {"settings.json", "personality.txt", "safety.json"}


def export_profile(
    output: Path,
    settings: dict[str, Any],
    profile_dirs: tuple[Path, ...] = (),
    reminders: list[dict[str, Any]] | None = None,
) -> None:
    manifest = {
        "format": "baymax-profile",
        "version": FORMAT_VERSION,
        "includes_reminders": reminders is not None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("settings.json", json.dumps(settings, indent=2))
        archive.writestr(
            "safety.json", json.dumps({"policy": "deterministic-built-in", "version": 1}, indent=2)
        )
        if reminders is not None:
            archive.writestr("reminders.json", json.dumps(reminders, indent=2))
        for directory in profile_dirs:
            if directory.exists():
                for path in directory.glob("*.toml"):
                    archive.write(path, f"model-profiles/{path.name}")


def import_profile(source: Path, destination: Path) -> dict[str, Any]:
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise ValueError("unsafe archive path")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "baymax-profile" or manifest.get("version") != FORMAT_VERSION:
            raise ValueError("unsupported profile format")
        settings = json.loads(archive.read("settings.json"))
        if not isinstance(settings, dict):
            raise ValueError("profile settings must be an object")
        with tempfile.TemporaryDirectory() as temporary:
            archive.extractall(temporary)
            source_profiles = Path(temporary) / "model-profiles"
            if source_profiles.exists():
                destination.mkdir(parents=True, exist_ok=True)
                for profile in source_profiles.glob("*.toml"):
                    shutil.copy2(profile, destination / profile.name)
        return settings

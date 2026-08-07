from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

FORMAT_NAME = "baymax-portable-profile"
FORMAT_VERSION = 2
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
SECRET_WORDS = ("secret", "password", "token", "api_key", "private_key", "credential")


@dataclass(frozen=True)
class ImportedProfile:
    settings: dict[str, Any]
    personality: dict[str, Any]
    safety: dict[str, Any]
    reminders: tuple[dict[str, Any], ...]
    source_version: int


def _safe_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _safe_data(item)
            for key, item in value.items()
            if not any(word in key.lower() for word in SECRET_WORDS)
        }
    if isinstance(value, (list, tuple)):
        return [_safe_data(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _json_bytes(value: Any) -> bytes:
    return json.dumps(_safe_data(value), indent=2, sort_keys=True).encode("utf-8")


def export_profile(
    output: Path,
    settings: dict[str, Any],
    profile_dirs: tuple[Path, ...] = (),
    reminders: list[dict[str, Any]] | None = None,
    personality: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
) -> None:
    files: dict[str, bytes] = {
        "settings.json": _json_bytes(settings),
        "personality.json": _json_bytes(
            personality or {"system_prompt": settings.get("system_prompt", "")}
        ),
        "safety.json": _json_bytes(safety or {"policy": "deterministic-built-in", "schema": 1}),
    }
    if reminders is not None:
        files["reminders.json"] = _json_bytes(reminders)
    for directory in profile_dirs:
        if directory.is_dir():
            for path in sorted(directory.glob("*.toml")):
                files[f"model-profiles/{path.name}"] = path.read_bytes()
    manifest = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "includes_reminders": reminders is not None,
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", _json_bytes(manifest))
        for name, content in files.items():
            archive.writestr(name, content)


def _migrate_v1(archive: zipfile.ZipFile) -> ImportedProfile:
    settings = json.loads(archive.read("settings.json"))
    safety = json.loads(archive.read("safety.json")) if "safety.json" in archive.namelist() else {}
    reminders = (
        json.loads(archive.read("reminders.json")) if "reminders.json" in archive.namelist() else []
    )
    return ImportedProfile(
        settings, {"system_prompt": settings.get("system_prompt", "")}, safety, tuple(reminders), 1
    )


def import_profile(source: Path, destination: Path) -> ImportedProfile:
    if source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("profile archive exceeds the 10 MiB safety limit")
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if sum(item.file_size for item in archive.infolist()) > MAX_ARCHIVE_BYTES:
            raise ValueError("expanded profile exceeds the 10 MiB safety limit")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or path.parts[0] == "":
                raise ValueError("unsafe archive path")
        manifest = json.loads(archive.read("manifest.json"))
        version = manifest.get("version")
        if version == 1 and manifest.get("format") in {"baymax-profile", FORMAT_NAME}:
            result = _migrate_v1(archive)
        elif version == FORMAT_VERSION and manifest.get("format") == FORMAT_NAME:
            expected = manifest.get("files", {})
            if not isinstance(expected, dict):
                raise ValueError("invalid profile manifest")
            if set(names) != {"manifest.json", *expected}:
                raise ValueError("profile contains undeclared files")
            for name, digest in expected.items():
                if name not in names or hashlib.sha256(archive.read(name)).hexdigest() != digest:
                    raise ValueError(f"profile checksum failed: {name}")
            settings = json.loads(archive.read("settings.json"))
            personality = json.loads(archive.read("personality.json"))
            safety = json.loads(archive.read("safety.json"))
            reminders = (
                json.loads(archive.read("reminders.json")) if "reminders.json" in names else []
            )
            if not all(
                isinstance(value, dict) for value in (settings, personality, safety)
            ) or not isinstance(reminders, list):
                raise ValueError("invalid profile component schema")
            result = ImportedProfile(settings, personality, safety, tuple(reminders), version)
        else:
            raise ValueError("unsupported profile format version")
        destination.mkdir(parents=True, exist_ok=True)
        for name in names:
            path = PurePosixPath(name)
            if (
                len(path.parts) == 2
                and path.parts[0] == "model-profiles"
                and path.suffix == ".toml"
            ):
                (destination / path.name).write_bytes(archive.read(name))
        return result

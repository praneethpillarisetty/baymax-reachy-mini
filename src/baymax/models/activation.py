from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path

from .registry import RuntimeModelRegistry

ProviderTest = Callable[[str], bool]


class ModelActivation:
    def __init__(
        self,
        data_dir: Path,
        registry: RuntimeModelRegistry,
        provider_test: ProviderTest | None = None,
    ):
        self.directory = data_dir / "config"
        self.active_path = self.directory / "active-models.json"
        self.backup_path = self.directory / "active-models.previous.json"
        self.registry = registry
        self.provider_test = provider_test or (lambda identifier: identifier == "mock-llm")

    def active(self) -> dict[str, str]:
        if not self.active_path.is_file():
            return {"llm": "mock-llm", "stt": "", "tts": "", "wake_word": ""}
        value = json.loads(self.active_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in value.items()
        ):
            raise ValueError("active model configuration is invalid")
        return value

    def activate(self, selected: dict[str, str]) -> dict[str, str]:
        if not selected.get("llm"):
            raise ValueError("an LLM selection is required")
        for purpose, identifier in selected.items():
            if not identifier:
                continue
            card = self.registry.require(identifier)
            if card.purpose != purpose:
                raise ValueError(f"{identifier} cannot be activated for {purpose}")
            if card.status != "verified":
                raise ValueError(f"{identifier} is unverified and cannot be activated")
            if card.installation_method != "built-in":
                manifest = self.directory.parent / "models" / identifier / "manifest.json"
                if not manifest.is_file():
                    raise ValueError(f"{identifier} is not installed and verified")
            if not self.provider_test(identifier):
                raise RuntimeError(f"provider test failed for {identifier}; activation rolled back")
        self.directory.mkdir(parents=True, exist_ok=True)
        staged = self.active_path.with_suffix(".staged")
        staged.write_text(json.dumps(selected, indent=2), encoding="utf-8")
        had_active = self.active_path.is_file()
        if had_active:
            shutil.copy2(self.active_path, self.backup_path)
        try:
            os.replace(staged, self.active_path)
            return self.active()
        except OSError:
            staged.unlink(missing_ok=True)
            if had_active and self.backup_path.is_file():
                shutil.copy2(self.backup_path, self.active_path)
            raise

    def rollback(self) -> dict[str, str]:
        if not self.backup_path.is_file():
            raise FileNotFoundError("no previous model configuration is available")
        current = self.active_path.with_suffix(".rollback-current")
        if self.active_path.is_file():
            shutil.copy2(self.active_path, current)
        try:
            os.replace(self.backup_path, self.active_path)
            if current.is_file():
                os.replace(current, self.backup_path)
            return self.active()
        except OSError:
            if current.is_file():
                os.replace(current, self.active_path)
            raise

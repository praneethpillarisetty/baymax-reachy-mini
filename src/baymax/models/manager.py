from __future__ import annotations

import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .activation import ModelActivation
from .capabilities import detect_capabilities, evaluate, recommended_target
from .installation_state import InstallationProgress, InstallationStateStore
from .installer import ModelInstaller
from .registry import RuntimeModelRegistry


class ModelManager:
    """Local model setup facade shared by CLI and localhost UI."""

    def __init__(self, data_dir: Path, registry_path: Path = Path("config/model-registry.toml")):
        self.data_dir = data_dir
        self.registry = RuntimeModelRegistry(registry_path)
        self.state = InstallationStateStore(data_dir / "setup/installation-state.json")
        self.installer = ModelInstaller(data_dir, self.state)
        self.activation = ModelActivation(data_dir, self.registry)
        self.events: list[dict[str, str]] = []
        self._worker: threading.Thread | None = None
        self._last_model = ""
        self._event_lock = threading.Lock()

    def setup_status(self) -> dict[str, Any]:
        capabilities = detect_capabilities(self.data_dir)
        return {
            "target": recommended_target(capabilities),
            "ready_for_simulator": True,
            "capabilities": capabilities.public_dict(),
            "notice": "Physical Reachy motion and unverified model activation are disabled.",
        }

    def cards(self) -> list[dict[str, Any]]:
        capabilities = detect_capabilities(self.data_dir)
        progress = self.state.load()
        result = []
        for card in self.registry.models().values():
            compatibility = evaluate(card, capabilities)
            value = asdict(card)
            value.update(
                {
                    "compatible": compatibility.compatible,
                    "compatibility_reasons": compatibility.reasons,
                    "installed": card.installation_method == "built-in",
                    "active": card.id in self.activation.active().values(),
                    "operation_active": progress.stage
                    in {
                        "checking",
                        "downloading",
                        "verifying",
                        "installing",
                        "testing",
                        "activating",
                    },
                }
            )
            result.append(value)
        return result

    def progress(self) -> dict[str, Any]:
        value = asdict(self.state.load())
        value["percentage"] = self.state.load().percentage
        return value

    def record(self, level: str, message: str) -> None:
        with self._event_lock:
            self.events.append({"level": level, "message": message[:500]})
            del self.events[:-100]

    def start_install(self, identifier: str, *, confirmed: bool) -> None:
        if not confirmed:
            raise ValueError("installation requires explicit confirmation")
        card = self.registry.require(identifier)
        self._last_model = identifier
        if self._worker and self._worker.is_alive():
            raise RuntimeError("another installation is already active")
        if card.installation_method == "built-in":
            self.state.save(InstallationProgress(card.id, "complete"))
            self.record("info", f"{card.id} is built in; no download was performed")
            return
        if card.status != "verified":
            raise RuntimeError("unverified models cannot be installed automatically")

        def run() -> None:
            try:
                self.installer.install_file(card)
                self.record("info", f"{card.id} installation completed")
            except (OSError, RuntimeError, ValueError) as exc:
                self.record("error", f"{card.id}: {exc}")

        self._worker = threading.Thread(target=run, daemon=True, name="baymax-model-install")
        self._worker.start()

    def control(self, action: str) -> None:
        if action == "pause":
            self.installer.pause()
        elif action == "resume":
            self.installer.resume()
        elif action == "retry":
            if self._worker and self._worker.is_alive():
                raise RuntimeError("cannot retry while an installation is active")
            if not self._last_model:
                raise RuntimeError("there is no previous installation to retry")
            self.installer.cancel_event.clear()
            self.start_install(self._last_model, confirmed=True)
        elif action == "cancel":
            self.installer.cancel()
        else:
            raise ValueError("control must be pause, resume, cancel, or retry")
        self.record("info", f"installation {action} requested")

    def test(self, identifier: str) -> dict[str, object]:
        card = self.registry.require(identifier)
        if card.status != "verified":
            raise ValueError("unverified models cannot be tested as supported providers")
        ok = self.activation.provider_test(identifier)
        self.record("info" if ok else "error", f"provider test for {identifier}: {ok}")
        return {"model_id": identifier, "ok": ok}

    def activate(self, selected: dict[str, str]) -> dict[str, str]:
        self.state.save(InstallationProgress(stage="activating"))
        try:
            active = self.activation.activate(selected)
        except (OSError, RuntimeError, ValueError):
            self.state.save(
                InstallationProgress(
                    stage="failed",
                    error="activation failed",
                    recovery="The previous configuration remains active. Correct the model and retry.",
                )
            )
            raise
        self.state.save(InstallationProgress(stage="complete"))
        self.record("info", "model configuration activated")
        return active

    def rollback(self) -> dict[str, str]:
        active = self.activation.rollback()
        self.record("warning", "model configuration rolled back after confirmation")
        return active

from __future__ import annotations

import json

import pytest

from baymax.cli import main
from baymax.config import Settings
from baymax.core.diagnostics import export_diagnostics
from baymax.core.readiness import capability_report


def test_lan_and_hardware_are_disabled_by_default():
    settings = Settings()
    assert settings.allow_ollama_lan is False
    assert settings.reachy_supervised is False
    assert settings.reachy_checklist_complete is False


def test_network_connection_requires_host():
    with pytest.raises(ValueError, match="requires BAYMAX_REACHY_HOST"):
        Settings(reachy_connection_mode="network").validate()


def test_movement_limit_is_bounded():
    with pytest.raises(ValueError, match="between 0 and 1"):
        Settings(reachy_max_movement=1.1).validate()


def test_smoke_requires_all_physical_confirmations(monkeypatch, capsys):
    monkeypatch.delenv("BAYMAX_ROBOT_BACKEND", raising=False)
    assert main(["robot-smoke", "--confirm-supervised"]) == 2
    assert "BAYMAX_ROBOT_BACKEND=reachy" in capsys.readouterr().err


def test_robot_status_describes_fail_closed_result(capsys):
    assert main(["robot-status"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["readiness"]["movement_enabled"] is False
    assert result["readiness"]["failure_result"] == "safe stop and shutdown; no movement"
    capabilities = result["capability_report"]
    assert capabilities["simulator_available"] is True
    assert capabilities["laptop_mode_available"] is True
    assert capabilities["physical_robot_connected"] is False
    assert capabilities["physical_validation_required"] is False


def test_capability_report_is_side_effect_free_and_explicit(monkeypatch):
    monkeypatch.setattr("baymax.core.readiness.shutil.which", lambda name: None)
    result = capability_report(Settings())
    assert result["ollama"] == {
        "configured": False,
        "executable_available": False,
        "lan_opt_in": False,
    }
    assert result["stt"] == {"backend": "mock", "configured": True}
    assert result["tts"] == {"backend": "console", "configured": True}
    assert result["reachy_sdk"]["official_wrapper_verified"] is False


def test_diagnostics_export_redacts_sensitive_fields(tmp_path):
    output = tmp_path / "diagnostics.json"
    export_diagnostics(Settings(database_path=tmp_path / "db.sqlite3"), output)
    payload = output.read_text(encoding="utf-8")
    assert str(tmp_path) not in payload
    assert '"excluded":' in payload
    assert "<redacted>" in payload

import json
import zipfile

from baymax.cli import main
from baymax.config import Settings
from baymax.core.transfer import export_profile, import_profile
from baymax.platform.linux_arm64 import validate_linux_arm64
from baymax.platform.windows import application_directories


def test_windows_directories(tmp_path):
    result = application_directories(tmp_path)
    assert result["logs"] == tmp_path / "BaymaxCompanion/logs"


def test_linux_arm64_validation(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "aarch64")
    validate_linux_arm64()


def test_non_loopback_ollama_requires_opt_in(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://192.168.1.2:11434")
    try:
        Settings.from_env()
    except ValueError as exc:
        assert "ALLOW_OLLAMA_LAN" in str(exc)
    else:
        raise AssertionError("LAN URL was accepted implicitly")


def test_versioned_profile_roundtrip(tmp_path):
    output = tmp_path / "profile.zip"
    export_profile(output, {"mode": "simulator"})
    with zipfile.ZipFile(output) as archive:
        assert json.loads(archive.read("manifest.json"))["version"] == 1
    assert import_profile(output, tmp_path / "profiles")["mode"] == "simulator"


def test_import_rejects_path_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../bad", "x")
    try:
        import_profile(archive, tmp_path / "profiles")
    except ValueError as exc:
        assert "unsafe" in str(exc)
    else:
        raise AssertionError("unsafe archive accepted")


def test_doctor_mock(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "db.sqlite3"))
    assert main(["doctor"]) == 0
    assert "PASS configuration" in capsys.readouterr().out


def test_data_delete_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "db.sqlite3"))
    assert main(["data", "delete"]) == 2

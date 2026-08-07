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
    export_profile(
        output,
        {"mode": "simulator", "system_prompt": "Be kind", "api_key": "never-export"},
        reminders=[{"title": "Water", "due_at": "soon", "completed": 0}],
        safety={"policy": "deterministic", "phrases": ["chest pain"]},
    )
    with zipfile.ZipFile(output) as archive:
        assert json.loads(archive.read("manifest.json"))["version"] == 2
        assert b"never-export" not in archive.read("settings.json")
    imported = import_profile(output, tmp_path / "profiles")
    assert imported.settings["mode"] == "simulator"
    assert imported.personality["system_prompt"] == "Be kind"
    assert imported.reminders[0]["title"] == "Water"


def test_v1_profile_migration(tmp_path):
    archive = tmp_path / "old.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": "baymax-profile", "version": 1}))
        z.writestr("settings.json", json.dumps({"mode": "simulator", "system_prompt": "Calm"}))
    imported = import_profile(archive, tmp_path / "profiles")
    assert imported.source_version == 1
    assert imported.personality["system_prompt"] == "Calm"


def test_profile_checksum_is_enforced(tmp_path):
    archive = tmp_path / "profile.zip"
    export_profile(archive, {"mode": "simulator"})
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(tampered, "w") as target:
        for item in source.infolist():
            content = source.read(item.filename)
            target.writestr(item, b"{}" if item.filename == "settings.json" else content)
    try:
        import_profile(tampered, tmp_path / "profiles")
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("tampered profile accepted")


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
    monkeypatch.setattr("baymax.core.doctor.sys.version_info", (3, 12, 0))
    assert main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "PASS python" in output
    assert "WARN physical Reachy support" in output


def test_doctor_reports_missing_local_audio_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "db.sqlite3"))
    monkeypatch.setenv("BAYMAX_ASR_BACKEND", "local-command")
    monkeypatch.setenv("BAYMAX_TTS_BACKEND", "local-command")
    monkeypatch.setattr("baymax.core.doctor.sys.version_info", (3, 12, 0))
    assert main(["doctor"]) == 1
    output = capsys.readouterr().out
    assert "FAIL ASR files: missing executable, model" in output
    assert "FAIL TTS files: missing executable, model" in output


def test_data_delete_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "db.sqlite3"))
    assert main(["data", "delete"]) == 2


def test_cli_profile_import_writes_settings_and_selected_reminders(tmp_path, monkeypatch):
    database = tmp_path / "db.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    archive = tmp_path / "portable.zip"
    export_profile(
        archive,
        {"mode": "simulator", "system_prompt": "Patient"},
        reminders=[{"title": "Water", "due_at": "09:00", "completed": 0}],
    )
    settings_output = tmp_path / "imported.json"
    assert (
        main(
            [
                "import",
                "--input",
                str(archive),
                "--profiles-dir",
                str(tmp_path / "profiles"),
                "--settings-output",
                str(settings_output),
                "--import-reminders",
            ]
        )
        == 0
    )
    assert json.loads(settings_output.read_text())["system_prompt"] == "Patient"
    from baymax.memory import LocalStore

    assert LocalStore(database).reminder_definitions()[0]["title"] == "Water"

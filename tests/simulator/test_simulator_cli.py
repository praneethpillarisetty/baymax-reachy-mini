import json

from baymax.cli import main


def test_simulator_cli_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "sim.sqlite3"))
    monkeypatch.setenv("BAYMAX_MODE", "simulator")
    monkeypatch.setenv("BAYMAX_LLM_BACKEND", "mock")
    assert main(["--once", "hello"]) == 0
    output = capsys.readouterr().out
    assert "I hear you" in output
    assert "Backend: mock" in output
    assert "Fallback: none" in output


def test_simulator_cli_once_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "sim.sqlite3"))
    monkeypatch.setenv("BAYMAX_MODE", "simulator")
    monkeypatch.setenv("BAYMAX_LLM_BACKEND", "mock")
    assert main(["--once", "hello", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["backend"] == "mock"
    assert output["fallback_reason"] is None
    assert "hello" in output["message"]

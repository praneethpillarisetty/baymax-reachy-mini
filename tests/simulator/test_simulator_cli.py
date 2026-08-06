from baymax.cli import main


def test_simulator_cli_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "sim.sqlite3"))
    monkeypatch.setenv("BAYMAX_MODE", "simulator")
    monkeypatch.setenv("BAYMAX_LLM_BACKEND", "mock")
    assert main(["--once", "hello"]) == 0
    assert "I hear you" in capsys.readouterr().out

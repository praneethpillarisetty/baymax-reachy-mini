import pytest

from baymax.robot.reachy_mini import ReachyConnectionError, ReachyMiniRobot


def test_reachy_adapter_import_and_construction_do_not_connect():
    robot = ReachyMiniRobot()
    assert not robot.connected
    assert not robot.stop_event.is_set()


def test_reachy_adapter_fails_closed_without_sdk(monkeypatch):
    robot = ReachyMiniRobot()
    monkeypatch.setattr(robot, "sdk_available", lambda: False)
    with pytest.raises(ReachyConnectionError, match="SDK import is unavailable"):
        robot.start()
    robot.shutdown()
    assert robot.stop_event.is_set()


def test_robot_smoke_requires_explicit_confirmation(tmp_path, monkeypatch):
    from baymax.cli import main

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "db.sqlite3"))
    assert main(["robot-smoke"]) == 2
    assert main(["robot-smoke", "--confirm-supervised"]) == 1

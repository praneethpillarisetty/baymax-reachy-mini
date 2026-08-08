from __future__ import annotations

import time
from typing import Any, Callable

import pytest

from baymax.robot.reachy_mini import (
    ReachyConnectionError,
    ReachyIntegrationNotVerified,
    ReachyMiniRobot,
)


class FakeSDK:
    def __init__(self, *, version: str = "test-1", verified: bool = True, timeout: bool = False):
        self.version, self.verified, self.timeout = version, verified, timeout
        self.connected = False
        self.stops = 0
        self.shutdowns = 0
        self.commands: list[tuple[str, float, float]] = []
        self.callback: Callable[[], None] | None = None

    def connect(self, mode: str, host: str | None, timeout: float) -> None:
        assert mode in {"local", "network"}
        assert timeout > 0
        if self.timeout:
            raise TimeoutError
        self.connected = True

    def register_safe_stop(self, callback: Callable[[], None]) -> bool:
        self.callback = callback
        return True

    def express(self, name: str, duration: float, movement: float) -> None:
        self.commands.append((name, duration, movement))

    def safe_stop(self) -> None:
        self.stops += 1

    def shutdown(self) -> None:
        self.shutdowns += 1
        self.connected = False

    def status(self) -> dict[str, Any]:
        return {"fake": True}


def test_missing_sdk_fails_closed(monkeypatch):
    monkeypatch.setattr(ReachyMiniRobot, "sdk_available", staticmethod(lambda: False))
    with pytest.raises(ReachyConnectionError, match="unavailable"):
        ReachyMiniRobot().start()


def test_import_is_not_treated_as_verified(monkeypatch):
    monkeypatch.setattr(ReachyMiniRobot, "sdk_available", staticmethod(lambda: True))
    with pytest.raises(ReachyIntegrationNotVerified, match="no officially verified"):
        ReachyMiniRobot().start()


def test_version_mismatch_fails_closed():
    sdk = FakeSDK(version="wrong")
    with pytest.raises(ReachyIntegrationNotVerified, match="version mismatch"):
        ReachyMiniRobot(sdk, expected_version="expected").start()


def test_connection_timeout_safe_stops_and_cleans_up():
    sdk = FakeSDK(timeout=True)
    robot = ReachyMiniRobot(sdk, expected_version="test-1")
    with pytest.raises(ReachyConnectionError, match="timed out"):
        robot.start()
    assert sdk.stops == 1
    assert sdk.shutdowns == 1
    assert robot.connected is False


def test_allow_list_and_motor_limits_are_enforced_before_sdk_call():
    sdk = FakeSDK()
    robot = ReachyMiniRobot(sdk, expected_version="test-1", max_movement=0.2)
    robot.start()
    with pytest.raises(ValueError, match="unsupported"):
        robot.express("freestyle")
    with pytest.raises(ValueError, match="movement"):
        robot.express("greeting", movement=0.21)
    with pytest.raises(ValueError, match="duration"):
        robot.express("greeting", duration=4)
    assert sdk.commands == []
    robot.express("greeting", duration=1, movement=0.2)
    assert sdk.commands == [("greeting", 1, 0.2)]
    robot.shutdown()


def test_watchdog_engages_safe_stop():
    sdk = FakeSDK()
    robot = ReachyMiniRobot(sdk, expected_version="test-1", watchdog_timeout=0.02)
    robot.start()
    deadline = time.monotonic() + 0.5
    while not robot.stop_event.is_set() and time.monotonic() < deadline:
        time.sleep(0.005)
    assert robot.stop_event.is_set()
    assert sdk.stops == 1
    robot.shutdown()


def test_unverified_fake_is_rejected():
    with pytest.raises(ReachyIntegrationNotVerified, match="not officially verified"):
        ReachyMiniRobot(FakeSDK(verified=False), expected_version="test-1").start()

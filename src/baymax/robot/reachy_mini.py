from __future__ import annotations

import importlib.util
import threading


class ReachyConnectionError(RuntimeError):
    """The physical SDK or verified connection is unavailable."""


class ReachyIntegrationNotVerified(ReachyConnectionError):
    """Official API metadata has not been verified in this checkout."""


class ReachyMiniRobot:
    """Fail-closed boundary for the physical Reachy Mini adapter.

    Importing and constructing this class never imports the optional SDK and never connects.
    Physical methods deliberately remain unavailable until the exact current Reachy Mini API and
    generated app lifecycle can be verified from official sources. This prevents an installed SDK
    from being mistaken for a tested physical connection.
    """

    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.connected = False

    @staticmethod
    def sdk_available() -> bool:
        return importlib.util.find_spec("reachy_mini") is not None

    def connect(self) -> None:
        if not self.sdk_available():
            raise ReachyConnectionError(
                "The official Reachy Mini SDK import is unavailable. Install the exact version "
                "required by the current official app template."
            )
        raise ReachyIntegrationNotVerified(
            "The SDK is installed, but its constructor and lifecycle have not been verified from "
            "the current official Reachy Mini documentation in this environment."
        )

    def start(self) -> None:
        self.connect()

    def express(self, emotion: str) -> None:
        raise ReachyConnectionError("Physical expression refused: no verified robot connection")

    def stop_motion(self) -> None:
        self.stop_event.set()

    def shutdown(self) -> None:
        self.stop_motion()
        self.connected = False

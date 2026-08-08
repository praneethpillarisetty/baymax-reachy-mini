from __future__ import annotations

import threading
from typing import Any

from .base import SAFE_EXPRESSIONS


class SimulatorRobot:
    def __init__(self):
        self.stop_event = threading.Event()
        self.started = False
        self.events: list[str] = []

    def start(self) -> None:
        self.connect()
        self.started = True
        self.stop_event.clear()
        self.events.append("safe_start")

    def connect(self) -> None:
        return

    def express(self, emotion: str) -> None:
        if emotion not in SAFE_EXPRESSIONS:
            raise ValueError("unsafe expression")
        if not self.stop_event.is_set():
            self.events.append(emotion)

    def stop_motion(self) -> None:
        self.stop_event.set()
        self.events.append("stop")

    def shutdown(self) -> None:
        self.stop_motion()
        self.started = False
        self.events.append("safe_shutdown")

    def status(self) -> dict[str, Any]:
        return {
            "backend": "simulator", "connected": self.started,
            "motion_stopped": self.stop_event.is_set(), "capabilities": ["expressions", "safe-stop"],
        }

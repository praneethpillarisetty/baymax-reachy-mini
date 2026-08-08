from __future__ import annotations

import importlib.metadata
import importlib.util
import threading
from collections.abc import Callable
from typing import Any, Protocol

from .base import SAFE_EXPRESSIONS


class ReachyConnectionError(RuntimeError):
    """The physical SDK or verified connection is unavailable."""


class ReachyIntegrationNotVerified(ReachyConnectionError):
    """Official API metadata has not been verified in this checkout."""


class ReachySDKBoundary(Protocol):
    """Baymax-owned seam implemented by a future verified official-SDK wrapper.

    This is intentionally not presented as an official SDK API. Tests inject fakes through this
    seam; production may use it only after a wrapper is reviewed against a recorded official SDK.
    """

    verified: bool
    version: str

    def connect(self, mode: str, host: str | None, timeout: float) -> None: ...
    def register_safe_stop(self, callback: Callable[[], None]) -> bool: ...
    def express(self, name: str, duration: float, movement: float) -> None: ...
    def safe_stop(self) -> None: ...
    def shutdown(self) -> None: ...
    def status(self) -> dict[str, Any]: ...


class ReachyMiniRobot:
    """Fail-closed, injectable boundary for supervised Reachy Mini integration."""

    EXPRESSIONS = frozenset(SAFE_EXPRESSIONS)

    def __init__(
        self,
        sdk: ReachySDKBoundary | None = None,
        *,
        expected_version: str | None = None,
        connection_mode: str = "local",
        host: str | None = None,
        connection_timeout: float = 5.0,
        watchdog_timeout: float = 10.0,
        max_duration: float = 3.0,
        max_movement: float = 0.25,
    ) -> None:
        self.sdk = sdk
        self.expected_version = expected_version
        self.connection_mode, self.host = connection_mode, host
        self.connection_timeout, self.watchdog_timeout = connection_timeout, watchdog_timeout
        self.max_duration, self.max_movement = max_duration, max_movement
        self.stop_event = threading.Event()
        self.connected = False
        self.safe_stop_registered = False
        self._watchdog: threading.Timer | None = None
        self._validate_limits()

    def _validate_limits(self) -> None:
        if self.connection_mode not in {"local", "network"}:
            raise ValueError("connection mode must be local or network")
        if self.connection_mode == "network" and not self.host:
            raise ValueError("network connection requires a host")
        for name, value in (
            ("connection timeout", self.connection_timeout),
            ("watchdog timeout", self.watchdog_timeout),
            ("maximum duration", self.max_duration),
        ):
            if value <= 0 or value > 60:
                raise ValueError(f"{name} must be greater than 0 and at most 60 seconds")
        if not 0 <= self.max_movement <= 1:
            raise ValueError("maximum movement must be between 0 and 1")

    @staticmethod
    def sdk_available() -> bool:
        return importlib.util.find_spec("reachy_mini") is not None

    @staticmethod
    def sdk_version() -> str | None:
        if not ReachyMiniRobot.sdk_available():
            return None
        for distribution in importlib.metadata.packages_distributions().get("reachy_mini", []):
            try:
                return importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                continue
        return "unknown"

    def connect(self) -> None:
        if self.sdk is None:
            if not self.sdk_available():
                raise ReachyConnectionError("The official Reachy Mini SDK import is unavailable")
            raise ReachyIntegrationNotVerified(
                "SDK import succeeded, but no officially verified Baymax wrapper is configured"
            )
        if not self.sdk.verified:
            raise ReachyIntegrationNotVerified("injected SDK wrapper is not officially verified")
        if self.expected_version is None or self.sdk.version != self.expected_version:
            raise ReachyIntegrationNotVerified(
                f"SDK version mismatch: expected {self.expected_version or '(unverified)'}, "
                f"found {self.sdk.version}"
            )
        try:
            self.sdk.connect(self.connection_mode, self.host, self.connection_timeout)
            self.safe_stop_registered = self.sdk.register_safe_stop(self.stop_motion)
            if not self.safe_stop_registered:
                raise ReachyConnectionError("safe-stop registration failed")
        except Exception as exc:
            self._cleanup_failure()
            if isinstance(exc, ReachyConnectionError):
                raise
            if isinstance(exc, TimeoutError):
                raise ReachyConnectionError("Reachy connection timed out") from exc
            raise ReachyConnectionError("Reachy connection failed") from exc
        self.connected = True

    def start(self) -> None:
        self.stop_event.clear()
        self.connect()
        self._arm_watchdog()

    def _arm_watchdog(self) -> None:
        if self._watchdog is not None:
            self._watchdog.cancel()
        self._watchdog = threading.Timer(self.watchdog_timeout, self.stop_motion)
        self._watchdog.daemon = True
        self._watchdog.start()

    def express(self, emotion: str, *, duration: float = 1.0, movement: float = 0.1) -> None:
        if emotion not in self.EXPRESSIONS:
            raise ValueError(f"unsupported Reachy expression: {emotion}")
        if duration <= 0 or duration > self.max_duration:
            raise ValueError(f"duration must be greater than 0 and at most {self.max_duration}")
        if movement < 0 or movement > self.max_movement:
            raise ValueError(f"movement must be between 0 and {self.max_movement}")
        if self.stop_event.is_set():
            raise ReachyConnectionError("physical expression cancelled by safe stop")
        if not self.connected or self.sdk is None:
            raise ReachyConnectionError("physical expression refused: adapter is stopped")
        try:
            self.sdk.express(emotion, duration, movement)
            self._arm_watchdog()
        except Exception as exc:
            self._cleanup_failure()
            raise ReachyConnectionError(
                "physical expression failed and safe-stop was engaged"
            ) from exc

    def stop_motion(self) -> None:
        self.stop_event.set()
        if self._watchdog is not None:
            self._watchdog.cancel()
            self._watchdog = None
        if self.sdk is not None:
            self.sdk.safe_stop()

    def _cleanup_failure(self) -> None:
        try:
            self.stop_motion()
        finally:
            if self.sdk is not None:
                self.sdk.shutdown()
            self.connected = False

    def shutdown(self) -> None:
        self._cleanup_failure()

    def status(self) -> dict[str, Any]:
        device = self.sdk.status() if self.sdk is not None else {}
        return {
            "backend": "reachy",
            "connected": self.connected,
            "motion_stopped": self.stop_event.is_set(),
            "sdk_import_available": self.sdk_available(),
            "sdk_version": self.sdk_version(),
            "sdk_verified": bool(self.sdk and self.sdk.verified and self.expected_version),
            "safe_stop_registered": self.safe_stop_registered,
            "motion_enabled": self.connected and not self.stop_event.is_set(),
            "device": device,
            "capabilities": ["injectable-sdk-boundary", "allow-listed-expressions", "safe-stop"],
        }

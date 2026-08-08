from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib import request
from urllib.error import HTTPError, URLError

from typing_extensions import Self

from .capabilities import SystemCapabilities, evaluate
from .installation_state import InstallationProgress, InstallationStateStore, Stage
from .registry import ModelCard
from .verification import verify_file, write_manifest


class DownloadResponse(Protocol):
    headers: object

    def read(self, size: int = -1) -> bytes: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> None: ...


Opener = Callable[[request.Request, float], DownloadResponse]


@dataclass(frozen=True)
class InstallationPlan:
    target: str
    models: tuple[ModelCard, ...]
    changes: tuple[str, ...]
    warnings: tuple[str, ...]


class ModelInstaller:
    def __init__(self, data_dir: Path, state: InstallationStateStore, opener: Opener | None = None):
        self.data_dir, self.state = data_dir, state
        self.opener = opener or (lambda req, timeout: request.urlopen(req, timeout=timeout))
        self.pause_event, self.cancel_event = threading.Event(), threading.Event()
        self._lock = threading.Lock()

    def plan(
        self, cards: list[ModelCard], target: str, capabilities: SystemCapabilities
    ) -> InstallationPlan:
        selected, warnings = [], []
        for card in cards:
            recommendation = (
                card.raspberry_pi_recommendation
                if target == "raspberry-pi"
                else card.laptop_recommendation
            )
            compatibility = evaluate(card, capabilities)
            if compatibility.compatible and "not recommended" not in recommendation:
                selected.append(card)
            else:
                warnings.append(f"{card.id}: {'; '.join(compatibility.reasons)}")
        changes = tuple(f"install {card.id} using {card.installation_method}" for card in selected)
        return InstallationPlan(target, tuple(selected), changes, tuple(warnings))

    def pause(self) -> None:
        self.pause_event.set()

    def resume(self) -> None:
        self.pause_event.clear()

    def cancel(self) -> None:
        self.cancel_event.set()

    def install_file(self, card: ModelCard, *, dry_run: bool = False) -> Path | None:
        if card.status != "verified" or not card.checksum:
            raise RuntimeError("automatic installation requires a verified card and checksum")
        if card.provider not in {"direct_file", "huggingface"}:
            raise RuntimeError("this provider does not use the safe file downloader")
        destination = self.data_dir / "models" / card.id / "model.bin"
        if dry_run:
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        if verify_file(card, destination).ok:
            return destination
        partial = destination.with_suffix(".partial")
        offset = partial.stat().st_size if partial.exists() else 0
        req = request.Request(card.source_url, headers={"Range": f"bytes={offset}-"})
        started = time.monotonic()
        self.state.save(InstallationProgress(card.id, "downloading", offset))
        try:
            with self._lock, self.opener(req, 30) as response, partial.open("ab") as output:
                headers = response.headers
                length = headers.get("Content-Length") if hasattr(headers, "get") else None
                total = offset + int(length) if length and str(length).isdigit() else None
                self._copy(response, output, card, offset, started, total)
            self.state.save(InstallationProgress(card.id, "verifying", partial.stat().st_size))
            result = verify_file(card, partial)
            if not result.ok:
                raise RuntimeError(result.detail)
            os.replace(partial, destination)
            write_manifest(destination.parent / "manifest.json", card, destination)
            self.state.save(
                InstallationProgress(
                    card.id, "complete", destination.stat().st_size, destination.stat().st_size
                )
            )
            return destination
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
            stage: Stage = "cancelled" if self.cancel_event.is_set() else "failed"
            self.state.save(
                InstallationProgress(
                    card.id,
                    stage,
                    partial.stat().st_size if partial.exists() else offset,
                    error=str(exc),
                    recovery="Retry to resume the preserved .partial file.",
                )
            )
            raise

    def _copy(
        self,
        response: DownloadResponse,
        output: BinaryIO,
        card: ModelCard,
        offset: int,
        started: float,
        total: int | None,
    ) -> None:
        downloaded = offset
        while chunk := response.read(64 * 1024):
            if self.cancel_event.is_set():
                raise RuntimeError("installation cancelled")
            while self.pause_event.is_set():
                self.state.save(InstallationProgress(card.id, "paused", downloaded))
                if self.cancel_event.wait(0.05):
                    raise RuntimeError("installation cancelled")
            output.write(chunk)
            downloaded += len(chunk)
            elapsed = max(time.monotonic() - started, 0.001)
            speed = max((downloaded - offset) / elapsed, 0.001)
            current = InstallationProgress(
                card.id,
                "downloading",
                downloaded,
                total,
                speed,
                (total - downloaded) / speed if total else None,
            )
            self.state.save(replace(current))

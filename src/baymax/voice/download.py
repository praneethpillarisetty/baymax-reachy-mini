from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePath, PureWindowsPath
from typing import BinaryIO, ClassVar
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse


class DownloadError(RuntimeError):
    """A safe, user-presentable download failure."""

    def __init__(self, code: str, message: str, recovery: str) -> None:
        super().__init__(message)
        self.code, self.recovery = code, recovery


@dataclass
class DownloadProgress:
    model_id: str
    state: str = "not installed"
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    current_file: str = ""
    error_code: str = ""
    message: str = "Not installed"
    recovery: str = ""


def application_voice_dir(platform: str | None = None, env: dict[str, str] | None = None) -> Path:
    """Return the platform application-data voice directory without touching the repository."""
    platform, env = platform or os.name, env or dict(os.environ)
    if platform == "nt":
        root = env.get("LOCALAPPDATA")
        if not root:
            root = str(Path.home() / "AppData" / "Local")
        return Path(root) / "BaymaxCompanion" / "models" / "voice"
    data_root = Path(env.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return data_root / "baymax-companion" / "models" / "voice"


def safe_filename(name: str) -> str:
    """Reject POSIX and Windows path traversal, drive names, and alternate data streams."""
    if not name or name in {".", ".."}:
        raise DownloadError(
            "unsafe_path",
            "The manifest contains an empty or unsafe file name.",
            "Use the versioned repository manifest.",
        )
    win = PureWindowsPath(name)
    if PurePath(name).name != name or win.name != name or win.drive or ":" in name:
        raise DownloadError(
            "unsafe_path",
            f"Unsafe destination file name: {name}",
            "Use the versioned repository manifest.",
        )
    return name


class DownloadManager:
    """Bounded, resumable downloader with persisted progress and atomic completion."""

    ACTIVE: ClassVar[set[str]] = {"downloading", "paused", "verifying"}

    def __init__(
        self,
        root: Path,
        *,
        opener=request.urlopen,
        free_space=None,
        retries: int = 3,
        timeout: float = 30,
        max_file_bytes: int = 3 * 1024**3,
        allow_http_for_tests: bool = False,
        sleep=time.sleep,
    ) -> None:
        self.root = root.resolve()
        self.state_dir = self.root / ".state"
        self.opener = opener
        self.free_space = free_space or (lambda path: shutil.disk_usage(path).free)
        self.retries, self.timeout, self.max_file_bytes = retries, timeout, max_file_bytes
        self.allow_http_for_tests, self.sleep = allow_http_for_tests, sleep
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._guards: dict[str, threading.Lock] = {}
        self._guard_lock = threading.Lock()

    def _state_path(self, model_id: str) -> Path:
        token = hashlib.sha256(model_id.encode()).hexdigest()
        return self.state_dir / f"{token}.json"

    def progress(self, model_id: str) -> DownloadProgress:
        try:
            return DownloadProgress(**json.loads(self._state_path(model_id).read_text("utf-8")))
        except (OSError, TypeError, json.JSONDecodeError):
            return DownloadProgress(model_id)

    def save(self, value: DownloadProgress) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self._state_path(value.model_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(value), indent=2), "utf-8")
        os.replace(temporary, path)

    def cancel(self) -> None:
        self._cancel.set()

    def pause(self) -> None:
        self._pause.set()

    def resume(self) -> None:
        self._pause.clear()

    def download(
        self,
        model_id: str,
        files: tuple[tuple[str, str, str | None, int | None], ...],
        destination: Path,
    ) -> None:
        with self._guard_lock:
            lock = self._guards.setdefault(model_id, threading.Lock())
        if not lock.acquire(blocking=False):
            raise DownloadError(
                "duplicate_download",
                f"A download for {model_id} is already running.",
                "Wait for it to finish or cancel it.",
            )
        self._cancel.clear()
        try:
            destination = destination.resolve()
            if destination != self.root and self.root not in destination.parents:
                raise DownloadError(
                    "unsafe_path",
                    "Destination escapes the voice model directory.",
                    "Use the application data directory.",
                )
            destination.mkdir(parents=True, exist_ok=True)
            completed = 0
            known_total = sum(size for _name, _url, _checksum, size in files if size is not None)
            all_sizes_known = all(size is not None for _n, _u, _c, size in files)
            for name, url, checksum, expected_size in files:
                self._download_file(
                    model_id,
                    safe_filename(name),
                    url,
                    checksum,
                    expected_size,
                    destination,
                    completed,
                    known_total if all_sizes_known else None,
                )
                completed += (destination / safe_filename(name)).stat().st_size
            previous = self.progress(model_id)
            self.save(
                DownloadProgress(
                    model_id,
                    "verified",
                    completed,
                    completed,
                    previous.current_file,
                    message="All files downloaded, atomically installed, and verified.",
                )
            )
        except DownloadError as exc:
            state = "cancelled" if exc.code == "cancelled" else "failed"
            prior = self.progress(model_id)
            prior.state, prior.error_code = state, exc.code
            prior.message, prior.recovery = str(exc), exc.recovery
            self.save(prior)
            raise
        finally:
            lock.release()

    def _download_file(
        self,
        model_id: str,
        name: str,
        url: str,
        checksum: str | None,
        expected_size: int | None,
        destination: Path,
        completed: int = 0,
        aggregate_total: int | None = None,
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" and not (self.allow_http_for_tests and parsed.scheme == "http"):
            raise DownloadError(
                "insecure_url",
                "Model downloads require HTTPS.",
                "Use an approved HTTPS URL from the repository manifest.",
            )
        final, partial = destination / name, destination / f"{name}.partial"
        offset = partial.stat().st_size if partial.exists() else 0
        self._preflight(url, name, expected_size)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                headers = {"User-Agent": "BaymaxCompanion/voice-setup"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                response = self.opener(request.Request(url, headers=headers), timeout=self.timeout)
                with response:
                    status = getattr(response, "status", None)
                    if status is None:
                        status = response.getcode()
                    if status not in {200, 206}:
                        raise DownloadError(
                            "http_status",
                            f"Download returned HTTP {status}.",
                            "Check the source status and retry.",
                        )
                    append = bool(offset and status == 206)
                    if offset and status == 200:
                        offset = 0
                    length = response.headers.get("Content-Length")
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "text/html" in content_type:
                        raise DownloadError(
                            "invalid_content",
                            f"The source returned HTML instead of model data for {name}.",
                            "Check the approved source URL and retry when the provider is available.",
                        )
                    response_checksum = (
                        (
                            response.headers.get("X-Linked-Etag")
                            or response.headers.get("ETag")
                            or ""
                        )
                        .strip('"')
                        .removeprefix("sha256:")
                    )
                    effective_checksum = checksum or (
                        response_checksum if len(response_checksum) == 64 else None
                    )
                    remaining = int(length) if length and length.isdigit() else None
                    total = (offset + remaining) if remaining is not None else expected_size
                    if expected_size is not None and total is not None and total < expected_size:
                        raise DownloadError(
                            "invalid_content",
                            f"The source response for {name} is smaller than expected.",
                            "Check the provider response and approved manifest, then retry.",
                        )
                    if total is not None and total > self.max_file_bytes:
                        raise DownloadError(
                            "size_limit",
                            f"{name} exceeds the configured file-size limit.",
                            "Review the approved manifest and available storage.",
                        )
                    needed = max(0, (total or self.max_file_bytes) - offset)
                    if self.free_space(destination) < needed + 64 * 1024**2:
                        raise DownloadError(
                            "insufficient_space",
                            f"Not enough free space for {name}.",
                            "Free disk space, then Retry to resume.",
                        )
                    self._stream(
                        model_id,
                        name,
                        response,
                        partial,
                        "ab" if append else "wb",
                        offset,
                        total,
                        completed,
                        aggregate_total,
                    )
                if expected_size is not None and partial.stat().st_size != expected_size:
                    raise DownloadError(
                        "size_mismatch",
                        f"Size verification failed for {name}.",
                        "Retry; if it repeats, inspect diagnostics and the manifest revision.",
                    )
                self.save(
                    DownloadProgress(
                        model_id,
                        "verifying",
                        completed + partial.stat().st_size,
                        aggregate_total or completed + partial.stat().st_size,
                        name,
                        message=f"Verifying {name}",
                    )
                )
                if effective_checksum and _sha256(partial).lower() != effective_checksum.lower():
                    partial.unlink(missing_ok=True)
                    raise DownloadError(
                        "checksum_mismatch",
                        f"Checksum verification failed for {name}; the unsafe partial file was deleted.",
                        "Do not activate it. Check the manifest revision and retry.",
                    )
                os.replace(partial, final)
                return
            except DownloadError:
                raise
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                self.sleep(min(2**attempt, 8))
                offset = partial.stat().st_size if partial.exists() else 0
        raise DownloadError(
            "network_error",
            f"Download failed after retries: {last_error}",
            "Check the network and source, then Retry to resume.",
        )

    def _preflight(self, url: str, name: str, expected_size: int | None) -> None:
        """Validate an approved URL cheaply; providers without HEAD support fall back to GET."""
        headers = {"User-Agent": "BaymaxCompanion/voice-setup"}
        try:
            response = self.opener(
                request.Request(url, headers=headers, method="HEAD"), timeout=self.timeout
            )
            with response:
                content_type = response.headers.get("Content-Type", "").lower()
                length = response.headers.get("Content-Length")
                if "text/html" in content_type:
                    raise DownloadError(
                        "invalid_content",
                        f"The source returned HTML instead of model data for {name}.",
                        "Check the approved manifest URL and provider status, then retry.",
                    )
                if expected_size is not None and length and int(length) < expected_size:
                    raise DownloadError(
                        "invalid_content",
                        f"The source response for {name} is smaller than expected.",
                        "Check the approved manifest URL and provider status, then retry.",
                    )
        except HTTPError as exc:
            if exc.code in {405, 501}:
                return
            raise DownloadError(
                f"http_{exc.code}",
                f"Model source preflight returned HTTP {exc.code} for {name}.",
                "Confirm provider access and retry; only manifest URLs may be used.",
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise DownloadError(
                "preflight_failed",
                f"Model source preflight failed for {name}: {exc}",
                "Check TLS, network access, and provider availability, then retry.",
            ) from exc

    def _stream(
        self,
        model_id: str,
        name: str,
        response: BinaryIO,
        partial: Path,
        mode: str,
        offset: int,
        total: int | None,
        completed: int = 0,
        aggregate_total: int | None = None,
    ) -> None:
        downloaded = offset
        with partial.open(mode) as output:
            while True:
                if self._cancel.is_set():
                    raise DownloadError(
                        "cancelled",
                        "Download cancelled; the partial file was preserved.",
                        "Choose Retry to resume it.",
                    )
                while self._pause.is_set():
                    self.save(
                        DownloadProgress(
                            model_id,
                            "paused",
                            completed + downloaded,
                            aggregate_total or (completed + total if total is not None else None),
                            name,
                            message="Download paused",
                        )
                    )
                    if self._cancel.wait(0.1):
                        raise DownloadError(
                            "cancelled",
                            "Download cancelled; the partial file was preserved.",
                            "Choose Retry to resume it.",
                        )
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                self.save(
                    DownloadProgress(
                        model_id,
                        "downloading",
                        completed + downloaded,
                        aggregate_total or (completed + total if total is not None else None),
                        name,
                        message=f"Downloading {name}",
                    )
                )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

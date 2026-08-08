from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .registry import ModelCard


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    detail: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(card: ModelCard, path: Path) -> VerificationResult:
    if not path.is_file():
        return VerificationResult(False, "model file is missing")
    if not card.checksum:
        return VerificationResult(False, "no published checksum is registered")
    if card.checksum == "built-in":
        return VerificationResult(True, "built-in adapter requires no artifact")
    actual = sha256(path)
    if actual.lower() != card.checksum.lower():
        return VerificationResult(False, f"SHA-256 mismatch (actual {actual})")
    return VerificationResult(True, "SHA-256 verified")


def verify_ollama_cli(model_name: str, timeout: float = 10) -> VerificationResult:
    try:
        result = subprocess.run(
            ["ollama", "list"], check=True, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return VerificationResult(False, "Ollama is missing; install it from ollama.com/download")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return VerificationResult(False, f"ollama list failed: {type(exc).__name__}")
    names = {line.split()[0] for line in result.stdout.splitlines()[1:] if line.split()}
    return VerificationResult(
        model_name in names,
        "model appears in ollama list" if model_name in names else "model is absent from ollama list",
    )


def write_manifest(path: Path, card: ModelCard, artifact: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema": 1, "model": asdict(card),
        "artifact": artifact.name if artifact else None,
        "verified_sha256": sha256(artifact) if artifact and artifact.is_file() else None,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


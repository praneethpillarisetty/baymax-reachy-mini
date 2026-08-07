from __future__ import annotations

import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .core.toml import load_toml

SUPPORTED_MODES = {"simulator", "laptop", "standalone", "reachy"}
SUPPORTED_BACKENDS = {"mock", "ollama", "litert"}
SECRET_MARKERS = ("KEY", "TOKEN", "PASSWORD", "SECRET")


def default_data_dir() -> Path:
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local")) / "BaymaxCompanion"
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "baymax-companion"


@dataclass(frozen=True)
class Settings:
    mode: str = "simulator"
    llm_backend: str = "mock"
    fallback_llm_backend: str | None = "mock"
    asr_backend: str = "mock"
    tts_backend: str = "console"
    asr_executable: Path | None = None
    asr_model_path: Path | None = None
    tts_executable: Path | None = None
    tts_model_path: Path | None = None
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout: float = 30.0
    ollama_retries: int = 2
    ollama_context_length: int = 4096
    ollama_temperature: float = 0.2
    allow_ollama_lan: bool = False
    litert_model_path: Path | None = None
    litert_model_profile: Path | None = None
    database_path: Path = default_data_dir() / "data/baymax.sqlite3"
    system_prompt: str = "You are a calm, kind, concise local wellness companion."

    @classmethod
    def from_toml(cls, path: Path | None = None) -> Settings:
        values: dict[str, Any] = {}
        if path:
            values.update(load_toml(path).get("baymax", {}))
        env_map = {
            "mode": "BAYMAX_MODE",
            "llm_backend": "BAYMAX_LLM_BACKEND",
            "fallback_llm_backend": "BAYMAX_FALLBACK_LLM_BACKEND",
            "asr_backend": "BAYMAX_ASR_BACKEND",
            "tts_backend": "BAYMAX_TTS_BACKEND",
            "asr_executable": "BAYMAX_ASR_EXECUTABLE",
            "asr_model_path": "BAYMAX_ASR_MODEL_PATH",
            "tts_executable": "BAYMAX_TTS_EXECUTABLE",
            "tts_model_path": "BAYMAX_TTS_MODEL_PATH",
            "ollama_url": "OLLAMA_URL",
            "ollama_model": "OLLAMA_MODEL",
            "ollama_timeout": "OLLAMA_TIMEOUT",
            "ollama_retries": "OLLAMA_RETRIES",
            "ollama_context_length": "OLLAMA_CONTEXT_LENGTH",
            "ollama_temperature": "OLLAMA_TEMPERATURE",
            "allow_ollama_lan": "BAYMAX_ALLOW_OLLAMA_LAN",
            "litert_model_path": "LITERT_MODEL_PATH",
            "litert_model_profile": "LITERT_MODEL_PROFILE",
            "database_path": "DATABASE_PATH",
            "system_prompt": "BAYMAX_SYSTEM_PROMPT",
        }
        for field, env in env_map.items():
            if env in os.environ:
                values[field] = os.environ[env]
        for key in ("ollama_timeout", "ollama_temperature"):
            if key in values:
                values[key] = float(values[key])
        for key in ("ollama_retries", "ollama_context_length"):
            if key in values:
                values[key] = int(values[key])
        if "allow_ollama_lan" in values:
            values["allow_ollama_lan"] = str(values["allow_ollama_lan"]).lower() in {
                "1",
                "true",
                "yes",
            }
        for key in (
            "asr_executable",
            "asr_model_path",
            "tts_executable",
            "tts_model_path",
            "litert_model_path",
            "litert_model_profile",
            "database_path",
        ):
            if values.get(key):
                values[key] = Path(values[key])
            elif key in values:
                values[key] = None
        settings = cls(**values)
        settings.validate()
        return settings

    @classmethod
    def from_env(cls) -> Settings:
        config = os.getenv("BAYMAX_CONFIG")
        return cls.from_toml(Path(config) if config else None)

    def validate(self) -> None:
        errors = []
        if self.mode not in SUPPORTED_MODES:
            errors.append(f"mode must be one of {sorted(SUPPORTED_MODES)}")
        if self.llm_backend not in SUPPORTED_BACKENDS:
            errors.append(f"backend must be one of {sorted(SUPPORTED_BACKENDS)}")
        if self.fallback_llm_backend and self.fallback_llm_backend not in SUPPORTED_BACKENDS:
            errors.append("invalid fallback backend")
        parsed = urlparse(self.ollama_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            errors.append("OLLAMA_URL must be an HTTP(S) URL")
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} and not self.allow_ollama_lan:
            errors.append("non-loopback Ollama requires BAYMAX_ALLOW_OLLAMA_LAN=true")
        if not 0 <= self.ollama_temperature <= 2:
            errors.append("temperature must be between 0 and 2")
        if errors:
            raise ValueError("; ".join(errors))

    def public_dict(self) -> dict[str, Any]:
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in asdict(self).items()
            if not any(marker in key.upper() for marker in SECRET_MARKERS)
        }

    @property
    def platform_summary(self) -> str:
        return f"{platform.system()} {platform.machine()} / Python {platform.python_version()}"

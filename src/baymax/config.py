from __future__ import annotations

import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .core.toml import load_toml

SUPPORTED_MODES = {"simulator", "laptop", "reachy"}
SUPPORTED_BACKENDS = {"mock", "ollama", "litert"}
SUPPORTED_VOICE_MODES = {"mock", "console", "local"}
SUPPORTED_ROBOT_BACKENDS = {"simulator", "reachy"}
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
SECRET_MARKERS = ("KEY", "TOKEN", "PASSWORD", "SECRET")
SENSITIVE_PATH_FIELDS = {
    "asr_executable", "asr_model_path", "tts_executable", "tts_model_path",
    "litert_model_path", "litert_tokenizer_path", "litert_model_profile",
    "data_dir", "database_path",
}


def default_data_dir() -> Path:
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local")) / "BaymaxCompanion"
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "baymax-companion"


@dataclass(frozen=True)
class Settings:
    mode: str = "simulator"
    llm_backend: str = "mock"
    fallback_llm_backend: str | None = "mock"
    voice_mode: str = "mock"
    robot_backend: str = "simulator"
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
    litert_tokenizer_path: Path | None = None
    litert_model_profile: Path | None = None
    data_dir: Path = default_data_dir()
    database_path: Path = default_data_dir() / "data/baymax.sqlite3"
    log_level: str = "INFO"
    system_prompt: str = "You are a calm, kind, concise local wellness companion."

    @classmethod
    def from_toml(cls, path: Path | None = None) -> Settings:
        values: dict[str, Any] = {}
        env_file = Path(os.getenv("BAYMAX_ENV_FILE", ".env"))
        if env_file.is_file():
            for number, raw in enumerate(env_file.read_text(encoding="utf-8").splitlines(), 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ValueError(f"invalid .env assignment at line {number}")
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
        if path:
            values.update(load_toml(path).get("baymax", {}))
        env_map = {
            "mode": "BAYMAX_MODE",
            "llm_backend": "BAYMAX_LLM_BACKEND",
            "fallback_llm_backend": "BAYMAX_FALLBACK_LLM_BACKEND",
            "voice_mode": "BAYMAX_VOICE_MODE",
            "robot_backend": "BAYMAX_ROBOT_BACKEND",
            "asr_backend": "BAYMAX_ASR_BACKEND",
            "tts_backend": "BAYMAX_TTS_BACKEND",
            "asr_executable": "ASR_EXECUTABLE",
            "asr_model_path": "ASR_MODEL_PATH",
            "tts_executable": "TTS_EXECUTABLE",
            "tts_model_path": "TTS_MODEL_PATH",
            "ollama_url": "OLLAMA_URL",
            "ollama_model": "OLLAMA_MODEL",
            "ollama_timeout": "OLLAMA_TIMEOUT",
            "ollama_retries": "OLLAMA_RETRIES",
            "ollama_context_length": "OLLAMA_CONTEXT_LENGTH",
            "ollama_temperature": "OLLAMA_TEMPERATURE",
            "allow_ollama_lan": "BAYMAX_ALLOW_OLLAMA_LAN",
            "litert_model_path": "LITERT_MODEL_PATH",
            "litert_tokenizer_path": "LITERT_TOKENIZER_PATH",
            "litert_model_profile": "LITERT_MODEL_PROFILE",
            "data_dir": "BAYMAX_DATA_DIR",
            "database_path": "DATABASE_PATH",
            "log_level": "BAYMAX_LOG_LEVEL",
            "system_prompt": "BAYMAX_SYSTEM_PROMPT",
        }
        for field, env in env_map.items():
            if env in os.environ:
                values[field] = os.environ[env]
        # Backwards-compatible aliases; the documented unprefixed variables take priority.
        for field in ("asr_executable", "asr_model_path", "tts_executable", "tts_model_path"):
            old = f"BAYMAX_{field.upper()}"
            if field not in values and old in os.environ:
                values[field] = os.environ[old]
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
            "litert_tokenizer_path",
            "litert_model_profile",
            "data_dir",
            "database_path",
        ):
            if values.get(key):
                values[key] = Path(values[key])
            elif key in values:
                values[key] = None
        if "database_path" not in values or values["database_path"] is None:
            data_dir = values.get("data_dir", default_data_dir())
            values["database_path"] = Path(data_dir) / "data/baymax.sqlite3"
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
        if self.voice_mode not in SUPPORTED_VOICE_MODES:
            errors.append(f"voice mode must be one of {sorted(SUPPORTED_VOICE_MODES)}")
        if self.robot_backend not in SUPPORTED_ROBOT_BACKENDS:
            errors.append(f"robot backend must be one of {sorted(SUPPORTED_ROBOT_BACKENDS)}")
        if self.mode == "reachy" and self.robot_backend != "reachy":
            errors.append("reachy mode requires BAYMAX_ROBOT_BACKEND=reachy")
        if self.mode != "reachy" and self.robot_backend == "reachy":
            errors.append("Reachy robot backend requires BAYMAX_MODE=reachy")
        if self.log_level.upper() not in SUPPORTED_LOG_LEVELS:
            errors.append(f"log level must be one of {sorted(SUPPORTED_LOG_LEVELS)}")
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
            key: "<redacted-path>" if key in SENSITIVE_PATH_FIELDS and value is not None
            else str(value) if isinstance(value, Path) else value
            for key, value in asdict(self).items()
            if not any(key.upper().endswith(marker) for marker in SECRET_MARKERS)
        }

    @property
    def platform_summary(self) -> str:
        return f"{platform.system()} {platform.machine()} / Python {platform.python_version()}"

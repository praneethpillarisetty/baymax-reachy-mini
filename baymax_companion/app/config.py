from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    mode: str = "simulator"
    llm_backend: str = "mock"
    fallback_llm_backend: str | None = None
    asr_backend: str = "mock"
    tts_backend: str = "console"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout: float = 30.0
    ollama_context_length: int = 4096
    ollama_temperature: float = 0.2
    litert_model_path: Path | None = None
    litert_model_profile: Path | None = None
    database_path: Path = Path("data/baymax.sqlite3")
    system_prompt: str = "You are a calm, kind, concise local wellness companion."

    @classmethod
    def from_env(cls) -> "Settings":
        def get_path(key: str) -> Path | None:
            value = os.getenv(key, "").strip()
            return Path(value) if value else None

        value = cls(
            mode=os.getenv("BAYMAX_MODE", "simulator"),
            llm_backend=os.getenv("BAYMAX_LLM_BACKEND", "mock"),
            fallback_llm_backend=os.getenv("BAYMAX_FALLBACK_LLM_BACKEND") or None,
            asr_backend=os.getenv("BAYMAX_ASR_BACKEND", "mock"),
            tts_backend=os.getenv("BAYMAX_TTS_BACKEND", "console"),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            ollama_timeout=float(os.getenv("OLLAMA_TIMEOUT", "30")),
            ollama_context_length=int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096")),
            ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
            litert_model_path=get_path("LITERT_MODEL_PATH"),
            litert_model_profile=get_path("LITERT_MODEL_PROFILE"),
            database_path=get_path("DATABASE_PATH") or Path("data/baymax.sqlite3"),
            system_prompt=os.getenv("BAYMAX_SYSTEM_PROMPT", cls.system_prompt),
        )
        if value.mode not in {"simulator", "reachy"}:
            raise ValueError("BAYMAX_MODE must be simulator or reachy")
        return value

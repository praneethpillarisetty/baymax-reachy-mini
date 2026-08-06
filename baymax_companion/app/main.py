from __future__ import annotations

import argparse
from pathlib import Path

from .config import Settings
from .memory import LocalStore
from .models.litert import LiteRTModel
from .models.mock import MockModel
from .models.ollama import OllamaModel
from .orchestrator import ConversationOrchestrator
from .robot.simulator import SimulatorRobot
from .safety import SafetyEngine
from .tools import ToolExecutor
from .voice.tts import ConsoleTTS


def build_model(settings: Settings, name: str):
    if name == "mock":
        return MockModel()
    if name == "ollama":
        return OllamaModel(
            settings.ollama_url,
            settings.ollama_model,
            settings.ollama_timeout,
            settings.ollama_context_length,
            settings.ollama_temperature,
        )
    if name == "litert":
        if settings.litert_model_path is None or settings.litert_model_profile is None:
            raise ValueError("LiteRT model and profile paths are required")
        return LiteRTModel(settings.litert_model_path, settings.litert_model_profile)
    raise ValueError(f"unknown model backend: {name}")


def build_app(settings: Settings) -> ConversationOrchestrator:
    if settings.mode != "simulator":
        raise RuntimeError("physical mode is locked pending supervised validation")
    store, robot, tts = LocalStore(settings.database_path), SimulatorRobot(), ConsoleTTS()
    robot.start()
    fallback = (
        build_model(settings, settings.fallback_llm_backend)
        if settings.fallback_llm_backend
        else None
    )
    return ConversationOrchestrator(
        build_model(settings, settings.llm_backend),
        SafetyEngine(),
        ToolExecutor(store),
        robot,
        tts,
        settings.system_prompt,
        fallback,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Local wellness companion")
    parser.add_argument("--once")
    parser.add_argument("--export-data", type=Path)
    parser.add_argument("--delete-data", action="store_true")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--safe-stop", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    store = LocalStore(settings.database_path)
    if args.export_data:
        store.export(args.export_data)
        return
    if args.delete_data:
        store.delete_all()
        return
    if args.health_check:
        print("ok: configuration and local database available")
        return
    app = build_app(settings)
    try:
        if args.safe_stop:
            app.robot.shutdown()
            return
        if args.once is not None:
            app.handle(args.once)
            return
        while (text := input("You: ").strip().lower()) not in {"quit", "exit"}:
            app.handle(text)
    finally:
        app.robot.shutdown()


if __name__ == "__main__":
    main()

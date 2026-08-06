from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .config import Settings
from .core.transfer import export_profile, import_profile
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
            settings.ollama_retries,
        )
    if name == "litert":
        if settings.litert_model_profile is None:
            raise ValueError("LITERT_MODEL_PROFILE is required")
        return LiteRTModel(
            settings.litert_model_profile, model_path_override=settings.litert_model_path
        )
    raise ValueError(f"unknown model backend: {name}")


def build_app(settings: Settings) -> ConversationOrchestrator:
    if settings.mode == "reachy":
        raise RuntimeError(
            "Reachy hardware mode is locked until the official adapter passes supervised validation"
        )
    robot, tts = SimulatorRobot(), ConsoleTTS()
    robot.start()
    fallback = (
        build_model(settings, settings.fallback_llm_backend)
        if settings.fallback_llm_backend and settings.fallback_llm_backend != settings.llm_backend
        else None
    )
    return ConversationOrchestrator(
        build_model(settings, settings.llm_backend),
        SafetyEngine(),
        ToolExecutor(LocalStore(settings.database_path)),
        robot,
        tts,
        settings.system_prompt,
        fallback,
    )


def doctor(settings: Settings) -> int:
    checks: list[tuple[str, bool, str]] = [
        ("configuration", True, "valid"),
        ("platform", True, settings.platform_summary),
    ]
    try:
        LocalStore(settings.database_path)
        checks.append(("database", True, str(settings.database_path)))
    except OSError as exc:
        checks.append(("database", False, str(exc)))
    if settings.llm_backend == "ollama":
        model = build_model(settings, "ollama")
        ok, detail = model.health_check()
        checks.append(("ollama", ok, detail))
    else:
        checks.append(("ollama", True, "not selected"))
    checks.append(("ollama executable", True, shutil.which("ollama") or "not installed (optional)"))
    if settings.llm_backend == "litert":
        assert settings.litert_model_profile is not None
        try:
            LiteRTModel(
                settings.litert_model_profile,
                dry_run=False,
                model_path_override=settings.litert_model_path,
            )
            checks.append(("litert model", True, "files available"))
        except Exception as exc:
            checks.append(("litert model", False, str(exc)))
    if settings.mode == "reachy":
        checks.append(("physical robot", False, "not hardware-validated"))
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    return 0 if all(ok for _, ok, _ in checks) else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="baymax")
    root.add_argument("--config", type=Path)
    root.add_argument("--once")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("doctor")
    config = commands.add_parser("config").add_subparsers(dest="config_command", required=True)
    config.add_parser("show")
    config.add_parser("validate")
    data = commands.add_parser("data").add_subparsers(dest="data_command", required=True)
    data_export = data.add_parser("export")
    data_export.add_argument("--output", type=Path, required=True)
    delete = data.add_parser("delete")
    delete.add_argument("--yes", action="store_true")
    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--include-reminders", action="store_true")
    imp = commands.add_parser("import")
    imp.add_argument("--input", type=Path, required=True)
    imp.add_argument("--profiles-dir", type=Path, default=Path("config/model-profiles"))
    commands.add_parser("safe-stop")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        settings = Settings.from_toml(args.config)
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    store = LocalStore(settings.database_path)
    if args.command == "doctor":
        return doctor(settings)
    if args.command == "config":
        if args.config_command == "show":
            print(json.dumps(settings.public_dict(), indent=2))
        else:
            print("Configuration is valid")
        return 0
    if args.command == "data":
        if args.data_command == "export":
            store.export(args.output)
            return 0
        if not args.yes:
            print("Refusing deletion without --yes", file=sys.stderr)
            return 2
        store.delete_all()
        return 0
    if args.command == "export":
        reminders = store.reminder_definitions() if args.include_reminders else None
        export_profile(
            args.output, settings.public_dict(), (Path("config/model-profiles"),), reminders
        )
        return 0
    if args.command == "import":
        imported = import_profile(args.input, args.profiles_dir)
        print(json.dumps(imported, indent=2))
        return 0
    app = build_app(settings)
    try:
        if args.command == "safe-stop":
            return 0
        if args.once is not None:
            app.handle(args.once)
            return 0
        while (text := input("You: ").strip()) not in {"quit", "exit"}:
            app.handle(text)
    finally:
        app.robot.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

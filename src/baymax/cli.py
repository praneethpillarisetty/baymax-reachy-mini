from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

from .config import Settings
from .core.diagnostics import export_diagnostics
from .core.doctor import doctor_exit_code, format_checks, run_doctor
from .core.readiness import capability_report
from .core.transfer import export_profile, import_profile
from .memory import LocalStore
from .models.capabilities import detect_capabilities, evaluate, recommended_target
from .models.installation_state import InstallationStateStore
from .models.installer import ModelInstaller
from .models.litert import LiteRTModel
from .models.manager import ModelManager
from .models.mock import MockModel
from .models.ollama import OllamaModel
from .models.registry import RuntimeModelRegistry
from .orchestrator import ConversationOrchestrator
from .robot.reachy_mini import ReachyConnectionError, ReachyMiniRobot
from .robot.simulator import SimulatorRobot
from .safety import SafetyEngine
from .tools import ToolExecutor
from .ui import run_ui
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
    if settings.robot_backend == "reachy":
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
        ToolExecutor(
            LocalStore(settings.database_path),
            simulator_mode=settings.mode == "simulator" and settings.robot_backend == "simulator",
        ),
        robot,
        tts,
        settings.system_prompt,
        fallback,
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="baymax")
    root.add_argument("--config", type=Path)
    root.add_argument("--once")
    root.add_argument("--json", action="store_true", dest="response_json")
    commands = root.add_subparsers(dest="command")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
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
    imp.add_argument("--settings-output", type=Path)
    imp.add_argument("--import-reminders", action="store_true")
    models = commands.add_parser("models").add_subparsers(dest="models_command", required=True)
    model_list = models.add_parser("list")
    model_list.add_argument("--registry", type=Path, default=Path("config/model-registry.toml"))
    models.add_parser("recommend").add_argument(
        "--registry", type=Path, default=Path("config/model-registry.toml")
    )
    plan = models.add_parser("plan")
    plan.add_argument("--target", choices=("auto", "laptop", "raspberry-pi"), default="auto")
    plan.add_argument("--registry", type=Path, default=Path("config/model-registry.toml"))
    install = models.add_parser("install")
    install.add_argument("--target", choices=("auto", "laptop", "raspberry-pi"), default="auto")
    install.add_argument("--registry", type=Path, default=Path("config/model-registry.toml"))
    install.add_argument("--dry-run", action="store_true")
    install.add_argument("--yes", action="store_true")
    models.add_parser("verify").add_argument("model_id", nargs="?")
    models.add_parser("test").add_argument("model_id", nargs="?")
    models.add_parser("status")
    activate = models.add_parser("activate")
    activate.add_argument("--llm", required=True)
    activate.add_argument("--stt", default="")
    activate.add_argument("--tts", default="")
    activate.add_argument("--wake-word", default="")
    activate.add_argument("--yes", action="store_true")
    rollback = models.add_parser("rollback")
    rollback.add_argument("--yes", action="store_true")
    inspect = models.add_parser("inspect")
    inspect.add_argument("--profile", type=Path, required=True)
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("model", type=Path)
    benchmark.add_argument("--label", required=True)
    commands.add_parser("robot-smoke").add_argument("--confirm-supervised", action="store_true")
    commands.add_parser("robot-status")
    commands.add_parser("robot-doctor")
    commands.add_parser("robot-safe-stop")
    commands.add_parser("safe-stop")
    diagnostics = commands.add_parser("diagnostics").add_subparsers(
        dest="diagnostics_command", required=True
    )
    diagnostics_export = diagnostics.add_parser("export")
    diagnostics_export.add_argument("--output", type=Path, default=Path("baymax-diagnostics.json"))
    ui = commands.add_parser("ui")
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument("--no-browser", action="store_true")
    voice_test = commands.add_parser("voice-test")
    voice_test.add_argument("component", choices=("microphone", "speaker", "asr", "tts"))
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
        checks = run_doctor(settings)
        print(format_checks(checks, args.json))
        return doctor_exit_code(checks)
    if args.command == "robot-doctor":
        checks = [check for check in run_doctor(settings) if "Reachy" in check.name]
        print(format_checks(checks))
        return doctor_exit_code(checks)
    if args.command == "diagnostics":
        export_diagnostics(settings, args.output)
        print(f"Redacted diagnostics exported to {args.output}")
        return 0
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
            args.output,
            settings.public_dict(),
            (Path("config/model-profiles"),),
            reminders,
            personality={"system_prompt": settings.system_prompt},
            safety=SafetyEngine.configuration(),
        )
        return 0
    if args.command == "import":
        imported = import_profile(args.input, args.profiles_dir)
        if args.settings_output:
            args.settings_output.parent.mkdir(parents=True, exist_ok=True)
            args.settings_output.write_text(
                json.dumps(imported.settings, indent=2), encoding="utf-8"
            )
        if args.import_reminders:
            store.import_reminder_definitions(imported.reminders)
        print(
            json.dumps(
                {
                    "source_version": imported.source_version,
                    "settings": imported.settings,
                    "personality": imported.personality,
                    "safety": imported.safety,
                    "reminders_available": len(imported.reminders),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "models":
        if args.models_command == "list":
            registry = RuntimeModelRegistry(args.registry)
            for card in registry.models().values():
                print(f"{card.id}\t{card.purpose}\t{card.provider}\t{card.status}")
        elif args.models_command == "inspect":
            adapter = LiteRTModel(args.profile, dry_run=True)
            print(
                json.dumps(
                    {
                        "profile": adapter.profile.id,
                        "model_path": str(adapter.model_path),
                        "tokenizer_path": str(adapter.tokenizer_path),
                        "signatures": adapter.inspect_signatures(),
                    },
                    indent=2,
                )
            )
        elif args.models_command in {"recommend", "plan", "install"}:
            registry = RuntimeModelRegistry(args.registry)
            capabilities = detect_capabilities(settings.data_dir)
            target = (
                recommended_target(capabilities)
                if getattr(args, "target", "auto") == "auto"
                else args.target
            )
            installer = ModelInstaller(
                settings.data_dir,
                InstallationStateStore(settings.data_dir / "setup/installation-state.json"),
            )
            plan = installer.plan(list(registry.models().values()), target, capabilities)
            if args.models_command == "recommend":
                for card in registry.models().values():
                    result = evaluate(card, capabilities)
                    print(
                        f"{card.id}: {'recommended' if result.compatible else 'not recommended'}"
                        f" — {'; '.join(result.reasons)}"
                    )
            else:
                print(
                    json.dumps(
                        {"target": target, "changes": plan.changes, "warnings": plan.warnings},
                        indent=2,
                    )
                )
                if args.models_command == "install" and not args.dry_run:
                    if not args.yes:
                        print("Refusing installation without --yes", file=sys.stderr)
                        return 2
                    for card in plan.models:
                        if card.installation_method != "built-in":
                            installer.install_file(card)
        elif args.models_command == "status":
            manager = ModelManager(settings.data_dir)
            print(
                json.dumps(
                    {"installation": manager.progress(), "models": manager.cards()}, indent=2
                )
            )
        elif args.models_command in {"verify", "test"}:
            identifier = args.model_id or "mock-llm"
            manager = ModelManager(settings.data_dir)
            operation = manager.verify if args.models_command == "verify" else manager.test
            try:
                operation_result = operation(identifier)
            except (KeyError, OSError, RuntimeError, ValueError) as exc:
                print(f"Model {args.models_command} failed: {exc}", file=sys.stderr)
                return 1
            print(json.dumps(operation_result, indent=2))
            return 0 if bool(operation_result["ok"]) else 1
        elif args.models_command == "activate":
            if not args.yes:
                print("Refusing activation without --yes", file=sys.stderr)
                return 2
            manager = ModelManager(settings.data_dir)
            print(
                json.dumps(
                    manager.activate(
                        {
                            "llm": args.llm,
                            "stt": args.stt,
                            "tts": args.tts,
                            "wake_word": args.wake_word,
                        }
                    ),
                    indent=2,
                )
            )
        elif args.models_command == "rollback":
            if not args.yes:
                print("Refusing rollback without --yes", file=sys.stderr)
                return 2
            print(json.dumps(ModelManager(settings.data_dir).rollback(), indent=2))
        return 0
    if args.command == "benchmark":
        if not args.model.is_file():
            print(f"Model artifact not found: {args.model}", file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "label": args.label,
                    "artifact": str(args.model),
                    "file_size_bytes": args.model.stat().st_size,
                    "runtime_verified": False,
                    "peak_ram_bytes": None,
                    "response_latency_seconds": None,
                    "status": "metadata-only; provide a verified runner before inference",
                },
                indent=2,
            )
        )
        return 0
    if args.command == "robot-smoke":
        if not args.confirm_supervised:
            print("Refusing hardware smoke test without --confirm-supervised", file=sys.stderr)
            return 2
        missing = []
        if settings.robot_backend != "reachy":
            missing.append("BAYMAX_ROBOT_BACKEND=reachy")
        if not settings.reachy_supervised:
            missing.append("BAYMAX_CONFIRM_SUPERVISED=true")
        if not settings.reachy_checklist_complete:
            missing.append("BAYMAX_PHYSICAL_CHECKLIST_COMPLETE=true")
        if missing:
            print(
                "Physical smoke test is fail-closed; missing: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        robot = ReachyMiniRobot()
        try:
            robot.start()
        except ReachyConnectionError as exc:
            print(f"Physical smoke test failed safely: {exc}", file=sys.stderr)
            return 1
        finally:
            robot.shutdown()
        print("Supervised Reachy Mini connection and safe shutdown passed.")
        return 0
    if args.command == "robot-status":
        status_robot = ReachyMiniRobot() if settings.robot_backend == "reachy" else SimulatorRobot()
        status = status_robot.status()
        status["capability_report"] = capability_report(
            settings, robot_connected=bool(status.get("connected"))
        )
        status["readiness"] = {
            "connection_mode": settings.reachy_connection_mode,
            "supervised_confirmation": settings.reachy_supervised,
            "physical_checklist_complete": settings.reachy_checklist_complete,
            "safe_stop": "registered" if status.get("safe_stop_registered") else "not registered",
            "movement_enabled": False,
            "limits": {
                "connection_timeout_seconds": settings.reachy_connection_timeout,
                "watchdog_timeout_seconds": settings.reachy_watchdog_timeout,
                "maximum_expression_duration_seconds": settings.reachy_max_expression_duration,
                "maximum_movement": settings.reachy_max_movement,
            },
            "failure_result": "safe stop and shutdown; no movement",
        }
        print(json.dumps(status, indent=2))
        return 0
    if args.command == "robot-safe-stop":
        stop_robot = ReachyMiniRobot() if settings.robot_backend == "reachy" else SimulatorRobot()
        stop_robot.stop_motion()
        stop_robot.shutdown()
        print("Safe stop engaged; movement remains disabled and the adapter is shut down.")
        return 0
    if args.command == "voice-test":
        backend = (
            settings.asr_backend
            if args.component in {"microphone", "asr"}
            else settings.tts_backend
        )
        if backend not in {"mock", "console"}:
            executable = (
                settings.asr_executable
                if args.component in {"microphone", "asr"}
                else settings.tts_executable
            )
            model = (
                settings.asr_model_path
                if args.component in {"microphone", "asr"}
                else settings.tts_model_path
            )
            if (
                executable is None
                or not executable.is_file()
                or model is None
                or not model.exists()
            ):
                print(
                    f"{args.component} unavailable: configure explicit executable and model paths",
                    file=sys.stderr,
                )
                return 1
        detail = (
            "bounded synthetic text preflight passed; temporary output cleanup is enabled"
            if args.component == "tts"
            else "microphone preflight passed; recordings are bounded and not retained"
        )
        print(f"{args.component} adapter health check passed ({backend}); {detail}")
        return 0
    app = build_app(settings)
    try:
        if args.command == "ui":
            if not 0 <= args.port <= 65535:
                print("UI port must be between 0 and 65535", file=sys.stderr)
                return 2
            run_ui(
                app,
                args.port,
                not args.no_browser,
                backend=settings.llm_backend,
                mode=settings.mode,
                voice=settings.voice_mode,
                robot=settings.robot_backend,
                model_manager=ModelManager(settings.data_dir),
            )
            return 0
        if args.command == "safe-stop":
            app.safe_stop()
            print("Safe stop engaged; model cancellation requested and expressions disabled.")
            return 0
        if args.once is not None:
            if args.response_json:
                # Console TTS must not corrupt the machine-readable response stream.
                with redirect_stdout(io.StringIO()):
                    response = app.handle(args.once)
            else:
                response = app.handle(args.once)
            if args.response_json:
                print(
                    json.dumps(
                        {
                            "message": response.message,
                            "emotion": response.emotion,
                            "actions": [
                                {"tool": action.tool, "arguments": action.arguments}
                                for action in response.actions
                            ],
                            "backend": response.backend,
                            "fallback_reason": response.fallback_reason,
                        }
                    )
                )
            else:
                print(f"Backend: {response.backend}")
                if response.fallback_reason is None:
                    print("Fallback: none")
                else:
                    print(f"Fallback reason: {response.fallback_reason}")
            return 0
        while (text := input("You: ").strip()) not in {"quit", "exit"}:
            app.handle(text)
    finally:
        app.robot.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

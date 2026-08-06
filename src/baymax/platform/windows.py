from pathlib import Path


def application_directories(local_app_data: Path) -> dict[str, Path]:
    root = local_app_data / "BaymaxCompanion"
    return {name: root / name for name in ("config", "models", "data", "logs")}

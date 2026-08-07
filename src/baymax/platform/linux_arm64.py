import platform


def validate_linux_arm64() -> None:
    if platform.system() != "Linux" or platform.machine().lower() not in {"aarch64", "arm64"}:
        raise RuntimeError("This deployment target requires Linux ARM64")

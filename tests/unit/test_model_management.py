import hashlib
import io
from dataclasses import replace
from pathlib import Path

from baymax.models.activation import ModelActivation
from baymax.models.capabilities import SystemCapabilities, evaluate, recommended_target
from baymax.models.installation_state import InstallationStateStore
from baymax.models.installer import ModelInstaller
from baymax.models.manager import ModelManager
from baymax.models.registry import RuntimeModelRegistry

REGISTRY = Path("config/model-registry.toml")


def capabilities(**changes):
    base = SystemCapabilities(
        "linux",
        "aarch64",
        "3.12",
        8192,
        20_000,
        "none",
        "none",
        "not probed",
        "not probed",
        False,
        False,
        False,
        "not probed",
    )
    return replace(base, **changes)


def test_runtime_registry_loads_complete_cards():
    cards = RuntimeModelRegistry(REGISTRY).models()
    assert cards["mock-llm"].status == "verified"
    assert cards["qwen3-4b-ollama"].source_url.startswith("https://ollama.com/")
    assert {card.purpose for card in cards.values()} == {"llm", "stt", "tts", "wake_word"}


def test_capability_rejections_explain_ram_disk_and_architecture():
    card = RuntimeModelRegistry(REGISTRY).require("qwen3-4b-ollama")
    result = evaluate(card, capabilities(ram_mb=1024, free_disk_mb=1, architecture="riscv64"))
    assert not result.compatible
    assert any("RAM" in reason for reason in result.reasons)
    assert any("disk" in reason for reason in result.reasons)
    assert any("architecture" in reason for reason in result.reasons)


def test_platform_target_detection():
    assert recommended_target(capabilities()) == "raspberry-pi"
    assert (
        recommended_target(capabilities(operating_system="windows", architecture="amd64"))
        == "laptop"
    )


class Response(io.BytesIO):
    def __init__(self, value: bytes):
        super().__init__(value)
        self.headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def downloadable(payload=b"complete model"):
    base = RuntimeModelRegistry(REGISTRY).require("faster-whisper-small")
    return replace(
        base,
        provider="direct_file",
        source_url="https://official.invalid/model",
        checksum=hashlib.sha256(payload).hexdigest(),
        status="verified",
    )


def test_dry_run_makes_no_changes(tmp_path):
    state = InstallationStateStore(tmp_path / "state.json")
    assert ModelInstaller(tmp_path, state).install_file(downloadable(), dry_run=True) is None
    assert not (tmp_path / "models").exists()


def test_resumable_download_uses_partial_and_verifies(tmp_path):
    payload, ranges = b"complete model", []
    partial = tmp_path / "models" / "faster-whisper-small" / "model.partial"
    partial.parent.mkdir(parents=True)
    partial.write_bytes(payload[:5])

    def open_download(req, timeout):
        ranges.append(req.headers["Range"])
        return Response(payload[5:])

    installer = ModelInstaller(
        tmp_path, InstallationStateStore(tmp_path / "state.json"), open_download
    )
    result = installer.install_file(downloadable(payload))
    assert result and result.read_bytes() == payload
    assert ranges == ["bytes=5-"]
    assert installer.state.load().stage == "complete"


def test_checksum_failure_preserves_partial_for_retry(tmp_path):
    card = replace(downloadable(), checksum="0" * 64)
    installer = ModelInstaller(
        tmp_path,
        InstallationStateStore(tmp_path / "state.json"),
        lambda req, timeout: Response(b"wrong"),
    )
    try:
        installer.install_file(card)
    except RuntimeError as exc:
        assert "mismatch" in str(exc)
    else:
        raise AssertionError("bad checksum accepted")
    assert installer.state.load().stage == "failed"
    assert (tmp_path / "models/faster-whisper-small/model.partial").exists()


def test_existing_valid_file_is_never_overwritten(tmp_path):
    payload = b"complete model"
    destination = tmp_path / "models/faster-whisper-small/model.bin"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    installer = ModelInstaller(
        tmp_path,
        InstallationStateStore(tmp_path / "state.json"),
        lambda req, timeout: (_ for _ in ()).throw(AssertionError("download attempted")),
    )
    assert installer.install_file(downloadable(payload)) == destination


def test_installation_cancellation_preserves_partial(tmp_path):
    installer = ModelInstaller(
        tmp_path,
        InstallationStateStore(tmp_path / "state.json"),
        lambda req, timeout: Response(b"complete model"),
    )
    installer.cancel()
    try:
        installer.install_file(downloadable())
    except RuntimeError as exc:
        assert "cancelled" in str(exc)
    else:
        raise AssertionError("cancelled download completed")
    assert installer.state.load().stage == "cancelled"


def test_transactional_activation_and_manual_rollback(tmp_path):
    activation = ModelActivation(tmp_path, RuntimeModelRegistry(REGISTRY))
    first = activation.activate({"llm": "mock-llm"})
    assert first == {"llm": "mock-llm"}
    second = activation.activate({"llm": "mock-llm", "stt": ""})
    assert second["stt"] == ""
    assert activation.rollback() == first


def test_failed_provider_test_preserves_active_configuration(tmp_path):
    registry = RuntimeModelRegistry(REGISTRY)
    working = ModelActivation(tmp_path, registry)
    working.activate({"llm": "mock-llm"})
    failing = ModelActivation(tmp_path, registry, provider_test=lambda identifier: False)
    try:
        failing.activate({"llm": "mock-llm", "tts": ""})
    except RuntimeError as exc:
        assert "rolled back" in str(exc)
    else:
        raise AssertionError("failed provider test activated")
    assert failing.active() == {"llm": "mock-llm"}


def test_unverified_model_cannot_activate(tmp_path):
    activation = ModelActivation(tmp_path, RuntimeModelRegistry(REGISTRY))
    try:
        activation.activate({"llm": "qwen3-4b-ollama"})
    except ValueError as exc:
        assert "unverified" in str(exc)
    else:
        raise AssertionError("unverified model activated")


def test_ollama_install_uses_declared_name_and_stays_unverified(tmp_path):
    pulled = []
    manager = ModelManager(tmp_path, ollama_pull=pulled.append)
    manager.start_install("qwen3-4b-ollama", confirmed=True)
    assert manager._worker is not None
    manager._worker.join(timeout=2)
    assert pulled == ["qwen3:4b"]
    assert manager.progress()["stage"] == "complete"
    try:
        manager.activate({"llm": "qwen3-4b-ollama"})
    except ValueError as exc:
        assert "unverified" in str(exc)
    else:
        raise AssertionError("unverified Ollama model activated")

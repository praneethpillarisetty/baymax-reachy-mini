from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from ..core.toml import load_toml
from .litert import LiteRTProfile

ModelPurpose = Literal["llm", "stt", "tts", "wake_word"]
ModelProvider = Literal["ollama", "huggingface", "direct_file", "executable"]


@dataclass(frozen=True)
class ModelCard:
    id: str
    purpose: ModelPurpose
    provider: ModelProvider
    source_url: str
    license_url: str
    checksum: str
    operating_systems: tuple[str, ...]
    architectures: tuple[str, ...]
    minimum_ram_mb: int
    minimum_disk_mb: int
    download_size_mb: int
    runtime_adapter: str
    installation_method: str
    verification_method: str
    laptop_recommendation: str
    raspberry_pi_recommendation: str
    status: Literal["verified", "unverified"]

    @classmethod
    def from_table(cls, identifier: str, value: dict[str, object]) -> ModelCard:
        def text(name: str) -> str:
            item = value.get(name)
            if not isinstance(item, str):
                raise ValueError(f"model {identifier}: {name} must be text")
            return item

        def integer(name: str) -> int:
            item = value.get(name)
            if not isinstance(item, int) or isinstance(item, bool) or item < 0:
                raise ValueError(f"model {identifier}: {name} must be a non-negative integer")
            return item

        purpose, provider, status = text("purpose"), text("provider"), text("status")
        if purpose not in {"llm", "stt", "tts", "wake_word"}:
            raise ValueError(f"model {identifier}: invalid purpose")
        if provider not in {"ollama", "huggingface", "direct_file", "executable"}:
            raise ValueError(f"model {identifier}: invalid provider")
        if status not in {"verified", "unverified"}:
            raise ValueError(f"model {identifier}: invalid status")
        return cls(
            identifier, cast(ModelPurpose, purpose), cast(ModelProvider, provider),
            text("source_url"), text("license_url"),
            text("checksum"), tuple(text("operating_systems").split(",")),
            tuple(text("architectures").split(",")), integer("minimum_ram_mb"),
            integer("minimum_disk_mb"), integer("download_size_mb"),
            text("runtime_adapter"), text("installation_method"),
            text("verification_method"), text("laptop_recommendation"),
            text("raspberry_pi_recommendation"),
            cast(Literal["verified", "unverified"], status),
        )


class RuntimeModelRegistry:
    def __init__(self, path: Path):
        self.path = path

    def models(self) -> dict[str, ModelCard]:
        data = load_toml(self.path)
        return {identifier: ModelCard.from_table(identifier, table) for identifier, table in data.items()}

    def require(self, identifier: str) -> ModelCard:
        try:
            return self.models()[identifier]
        except KeyError as exc:
            raise KeyError(f"unknown runtime model: {identifier}") from exc


class ModelProfileRegistry:
    def __init__(self, directories: tuple[Path, ...]):
        self.directories = directories

    def profiles(self) -> dict[str, tuple[Path, LiteRTProfile]]:
        result: dict[str, tuple[Path, LiteRTProfile]] = {}
        for directory in self.directories:
            if directory.is_dir():
                for path in sorted(directory.glob("*.toml")):
                    profile = LiteRTProfile.load(path)
                    if profile.id in result:
                        raise ValueError(f"duplicate model profile id: {profile.id}")
                    result[profile.id] = (path, profile)
        return result

    def require(self, identifier: str) -> tuple[Path, LiteRTProfile]:
        try:
            return self.profiles()[identifier]
        except KeyError as exc:
            raise KeyError(f"unknown model profile: {identifier}") from exc

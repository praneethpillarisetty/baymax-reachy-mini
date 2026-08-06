from __future__ import annotations

from pathlib import Path

from .litert import LiteRTProfile


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

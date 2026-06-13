"""Spec dataclasses — the parameter surface an agent authors against."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class PortraitSpec:
    kind: str = "portrait"
    archetype: str = "slime"
    seed: int = 0
    size: int = 512
    name: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BackgroundSpec:
    kind: str = "background"
    biome: str = "meadow"
    seed: int = 0
    width: int = 1152
    height: int = 648
    name: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_FIELDS = {
    "portrait": {"kind", "archetype", "seed", "size", "name"},
    "background": {"kind", "biome", "seed", "width", "height", "name"},
}


def spec_from_dict(data: dict):
    kind = data.get("kind")
    if kind == "portrait":
        return PortraitSpec(**{k: v for k, v in data.items() if k in _FIELDS[kind]})
    if kind == "background":
        return BackgroundSpec(**{k: v for k, v in data.items() if k in _FIELDS[kind]})
    raise ValueError(f"unknown kind {kind!r}")

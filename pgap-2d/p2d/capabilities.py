"""Machine-readable contract + fail-closed validation (pgap invariant)."""

from __future__ import annotations

from . import __version__
from .background import BIOMES
from .portrait import ARCHETYPES
from .spec import _FIELDS

SCHEMA_VERSION = 1


def capability_report() -> dict:
    return {
        "pipeline": "2d",
        "version": __version__,
        "schemaVersion": SCHEMA_VERSION,
        "kinds": {
            "portrait": {
                "archetypes": list(ARCHETYPES),
                "params": {"seed": "int", "size": "int 64..2048", "name": "str?"},
                "output": {"format": "png", "role": "Portrait"},
            },
            "background": {
                "biomes": sorted(BIOMES.keys()),
                "params": {"seed": "int", "width": "int 128..4096",
                           "height": "int 128..4096", "name": "str?"},
                "output": {"format": "png", "role": "BattleBackdrop"},
            },
        },
        "determinism": "same (spec, seed) -> byte-identical PNG",
    }


def validate_spec(data: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    kind = data.get("kind")
    if kind not in _FIELDS:
        return False, [f"unknown kind {kind!r}; supported: {sorted(_FIELDS)}"]

    unknown = set(data) - _FIELDS[kind]
    if unknown:
        errors.append(f"unknown fields for kind {kind!r}: {sorted(unknown)}")

    seed = data.get("seed", 0)
    if not isinstance(seed, int):
        errors.append("seed must be an int")

    if kind == "portrait":
        archetype = data.get("archetype", "slime")
        if archetype not in ARCHETYPES:
            errors.append(f"unknown archetype {archetype!r}; supported: {ARCHETYPES}")
        size = data.get("size", 512)
        if not isinstance(size, int) or not 64 <= size <= 2048:
            errors.append("size must be an int in 64..2048")
    else:
        biome = data.get("biome", "meadow")
        if biome not in BIOMES:
            errors.append(f"unknown biome {biome!r}; supported: {sorted(BIOMES)}")
        for dim in ("width", "height"):
            v = data.get(dim, 1152 if dim == "width" else 648)
            if not isinstance(v, int) or not 128 <= v <= 4096:
                errors.append(f"{dim} must be an int in 128..4096")

    return not errors, errors

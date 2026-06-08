"""Machine-readable capability report (the fail-closed contract an LLM authors to)."""

from __future__ import annotations

from typing import Any, Dict

from .spec import (
    BIOMES,
    LAYERS_BY_BIOME,
    RANGES,
    RESOLUTIONS,
    SCATTER_BY_BIOME,
)

CAPABILITIES_SCHEMA_VERSION = "psl.capabilities.v1"

# Biome -> sky/lighting/post profile hint the bridge realizes (SkyProfile role).
SKY_PROFILE_BY_BIOME = {
    "plain": "clear_day",
    "forest": "soft_gi_godrays",
    "snow": "cool_low_sun_fog",
    "ocean": "bright_reflective",
    "shore": "warm_day",
    "moon": "black_sky_harsh_sun",
}

# Biome -> whether a water plane (WaterPlane role) is expected.
WATER_BY_BIOME = {b: b in ("ocean", "shore") for b in BIOMES}

# Handoff roles this pipeline emits (see SPLIT.md). v1 implements Heightmap; the
# rest are declared so the contract is visible and lands in L1–L5.
HANDOFF_ROLES = [
    "Heightmap",
    "Weightmap:<layer>",
    "LandscapeMaterialSpec",
    "FoliageRule",
    "WaterPlane",
    "SkyProfile",
]

IMPLEMENTED = ["Heightmap", "LandscapeMaterialSpec", "Weightmap:<layer>", "FoliageRule"]  # L0–L2


def capabilities() -> Dict[str, Any]:
    return {
        "schemaVersion": CAPABILITIES_SCHEMA_VERSION,
        "generator": "psl",
        "status": "L2 (heightmap + weightmaps + material spec + scatter rules)",
        "biomes": list(BIOMES),
        "layersByBiome": {b: list(LAYERS_BY_BIOME[b]) for b in BIOMES},
        "scatterByBiome": {b: list(SCATTER_BY_BIOME[b]) for b in BIOMES},
        "skyProfileByBiome": dict(SKY_PROFILE_BY_BIOME),
        "waterByBiome": dict(WATER_BY_BIOME),
        "resolutions": list(RESOLUTIONS),
        "ranges": {k: list(v) for k, v in RANGES.items()},
        "handoffRoles": list(HANDOFF_ROLES),
        "implementedRoles": list(IMPLEMENTED),
    }

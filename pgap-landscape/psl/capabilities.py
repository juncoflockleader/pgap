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

# Default *submerged fraction* per water biome (used when the spec leaves seaLevel
# at 0): the sea level is then the field's percentile that submerges this fraction,
# so it's seed-stable. Ocean is mostly sea; shore is a ~third-submerged coastline.
SUBMERGED_TARGET_BY_BIOME = {"ocean": 0.62, "shore": 0.32}

# Biome -> water surface color (sRGB 0..255) hint for the WaterPlane material.
WATER_COLOR_BY_BIOME = {
    "ocean": (24, 64, 96), "shore": (46, 110, 130),
}

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

IMPLEMENTED = ["Heightmap", "LandscapeMaterialSpec", "Weightmap:<layer>",
               "FoliageRule", "WaterPlane"]  # L0–L4


def capabilities() -> Dict[str, Any]:
    return {
        "schemaVersion": CAPABILITIES_SCHEMA_VERSION,
        "generator": "psl",
        "status": "L4 (heightmap + weightmaps + material + scatter + water plane)",
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

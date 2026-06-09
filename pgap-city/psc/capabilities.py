"""Machine-readable capability report for pgap-city."""

from __future__ import annotations

from typing import Any, Dict

from .spec import CELLS, CULTURES, ERAS
from .styles import MODULE_KINDS, STYLE_PROFILES

CAPABILITIES_SCHEMA_VERSION = "psc.capabilities.v1"

# Handoff roles this pipeline emits (see SPLIT.md).
HANDOFF_ROLES = [
    "BuildingKit:<id>", "CityLayout", "CityInstancing", "StyleMaterialSpec",
    "RoadNetwork", "PropKit:<kind>",
]
IMPLEMENTED = ["CityLayout", "CityInstancing", "StyleMaterialSpec",
               "BuildingKit:<id>", "RoadNetwork", "PropKit:<kind>"]
STREET_NETS = ["grid", "fine_grid", "organic", "curved_industrial"]


def capabilities() -> Dict[str, Any]:
    prop_kinds = sorted({k for p in STYLE_PROFILES.values() for k in p["props"]})
    return {
        "schemaVersion": CAPABILITIES_SCHEMA_VERSION,
        "generator": "psc",
        "status": "C2+ (per-style street nets, skinned building kits, roads, prop scatter)",
        "eras": list(ERAS),
        "cultures": list(CULTURES),
        "cells": [f"{e}x{c}" for e, c in CELLS],
        "streetNets": list(STREET_NETS),
        "moduleKinds": list(MODULE_KINDS),
        "propKinds": prop_kinds,
        "ranges": {"sizeBlocks": [1, 16], "density": [0.0, 1.0]},
        "spec": {"era": "modern|futuristic", "culture": "american|japan|cyberpunk|steampunk",
                 "seed": "int", "sizeBlocks": "[cols,rows]", "density": "0..1?",
                 "landmarks": "[str]?", "terrain": "{extentM?,seaLevelM?}?"},
        "describe": "natural-language prompt -> spec (psc.nl.prompt_to_spec / --describe)",
        "profiles": {
            f"{e}x{c}": {
                "streetNet": p["streetNet"],
                "floors": p["floors"],
                "roof": p["roof"],
                "palette": p["palette"],
                "props": p["props"],
            }
            for (e, c), p in STYLE_PROFILES.items()
        },
        "handoffRoles": list(HANDOFF_ROLES),
        "implementedRoles": list(IMPLEMENTED),
    }

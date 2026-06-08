"""Machine-readable capability report for pgap-city."""

from __future__ import annotations

from typing import Any, Dict

from .spec import CELLS, CULTURES, ERAS
from .styles import MODULE_KINDS, STYLE_PROFILES

CAPABILITIES_SCHEMA_VERSION = "psc.capabilities.v1"

# Handoff roles this pipeline emits (see SPLIT.md). v1 implements CityLayout +
# StyleMaterialSpec; BuildingKit / RoadNetwork / PropScatter land in C1+.
HANDOFF_ROLES = [
    "BuildingKit:<id>",
    "CityLayout",
    "PropScatter",
    "StyleMaterialSpec",
    "RoadNetwork",
]
IMPLEMENTED = ["CityLayout", "StyleMaterialSpec"]  # C0


def capabilities() -> Dict[str, Any]:
    return {
        "schemaVersion": CAPABILITIES_SCHEMA_VERSION,
        "generator": "psc",
        "status": "scaffold (C0: layout grammar)",
        "eras": list(ERAS),
        "cultures": list(CULTURES),
        "cells": [f"{e}x{c}" for e, c in CELLS],
        "moduleKinds": list(MODULE_KINDS),
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

"""Machine-readable capability report for pgap-gear."""

from __future__ import annotations

from typing import Any, Dict

from .materials import MATERIALS
from .registry import SIZE_SCALE, TEMPLATES

SCHEMA_VERSION = "pgear.capabilities.v1"
HANDOFF_ROLES = ["GearMesh:<name>", "GearImport", "GearPreview"]


def capabilities() -> Dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generator": "pgear",
        "status": "v1 (rigid gear kit: weapons, shields, catalysts, and held tools)",
        "templates": {n: {"variants": t["variants"], "category": t["category"]}
                      for n, t in TEMPLATES.items()},
        "sizes": list(SIZE_SCALE),
        "materials": sorted(MATERIALS),
        "materialSlots": ["metal", "grip", "accent", "wood"],
        "spec": {"template": "str", "variant": "str|auto", "material": "freeform str",
                 "size": "small|normal|large|huge", "seed": "int", "name": "str?"},
        "describe": "natural-language prompt -> spec (pgear.nl.prompt_to_spec / --describe)",
        "output": ["SM_<name>.gltf", "<name>_Preview.png", "<name>.import.json", "manifest.json"],
        "handoffRoles": list(HANDOFF_ROLES),
        "note": ("Rigid static-mesh gear (no skin). Worn apparel/armor skinned to a "
                 "character skeleton is a future path (reuses pgap-3d-actor rigs)."),
    }

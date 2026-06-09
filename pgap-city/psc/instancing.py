"""Group a city layout's building instances into per-kit bulk-instancing payloads
ready for the unreal-mcp-rx `editor_instances_place` tool (one HISM component per
kit holding N instances, instead of N actors).

Each instance carries a world-space transform: location in cm (UE units), a yaw
rotation about up, and a 3-axis scale (the unit-box multiplier [width, depth,
height] in metres). The consumer imports SM_<kit>.gltf, sets the payload's
`mesh_path` to the resulting StaticMesh, and sends one call per kit.
"""

from __future__ import annotations

from typing import Any, Dict, List

SCHEMA_VERSION = "psc.city.instancing.v1"


def _transform(inst: Dict[str, Any]) -> Dict[str, Any]:
    sx, sy, sz = inst["scale3"]
    return {
        "location": {"x": inst["x"], "y": inst["y"], "z": inst.get("z", 0.0)},
        "rotation": {"pitch": 0.0, "yaw": float(inst["yaw"]), "roll": 0.0},
        "scale": {"x": sx, "y": sy, "z": sz},
    }


def instancing_payloads(layout: Dict[str, Any]) -> Dict[str, Any]:
    """Build the per-kit `editor_instances_place` payload bundle for a layout —
    buildings, roads, and props (all share kit + location/yaw/scale3)."""
    by_kit: Dict[str, List[Dict[str, Any]]] = {}
    for inst in (layout["instances"] + layout.get("road_instances", [])
                 + layout.get("prop_instances", [])):
        by_kit.setdefault(inst["kit"], []).append(_transform(inst))

    kits = []
    for kit in sorted(by_kit):
        transforms = by_kit[kit]
        kits.append({
            "kit": kit,
            "meshFile": f"SM_{kit}.gltf",
            "count": len(transforms),
            # ready-to-send editor_instances_place args; set mesh_path after import.
            "payload": {
                "mesh_path": "",   # the imported StaticMesh path for SM_<kit>.gltf
                "hierarchical": True,
                "label": f"{kit}_HISM",
                "instances": transforms,
            },
        })

    return {
        "schemaVersion": SCHEMA_VERSION,
        "tool": "editor_instances_place",
        "note": ("One editor_instances_place call per kit. Import each meshFile "
                 "(BuildingKit role), then set payload.mesh_path to the resulting "
                 "StaticMesh and send. Locations are cm; scale is [w,d,h] in m."),
        "units": {"location": "cm", "rotation": "deg", "scale": "m_multiplier"},
        "kits": kits,
        "totalInstances": sum(k["count"] for k in kits),
    }

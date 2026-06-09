"""Deterministic city layout grammar (C0: a block grid -> lots -> instances).

Emits **instance transforms** (kit ref + position + rotation + scale + variation
seed + zone), not geometry — the bridge bulk-instances them (HISM). Organic /
fine-grid / curved-industrial street nets are stylistic refinements over this grid
base (C2–C4); C0 lays a regular grid for every cell so the layout contract and the
engine round-trip can be stood up. All randomness flows from one seeded PCG64.

Units: centimeters (UE world units). Z=0 (terrain hook lands in C5).
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

M = 100.0  # meters -> cm


def _zone_for(rng: np.random.Generator) -> str:
    return str(rng.choice(["residential", "market", "civic"], p=[0.6, 0.3, 0.1]))


def generate_layout(profile: dict, size_blocks, seed: int, density: float) -> Dict[str, Any]:
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    cols, rows = int(size_blocks[0]), int(size_blocks[1])
    block = float(profile["blockSizeM"])
    street = float(profile["streetWidthM"])
    lots_x, lots_y = profile["lotsPerBlock"]
    fmin, fmax = profile["floors"]
    fh = float(profile["floorHeightM"])
    pitch = block + street

    streets: List[Dict[str, Any]] = []
    for c in range(cols + 1):
        x = c * pitch
        streets.append({"axis": "v", "x_m": x, "from_m": 0.0, "to_m": rows * pitch})
    for r in range(rows + 1):
        y = r * pitch
        streets.append({"axis": "h", "y_m": y, "from_m": 0.0, "to_m": cols * pitch})

    blocks: List[Dict[str, Any]] = []
    instances: List[Dict[str, Any]] = []
    props: List[Dict[str, Any]] = []
    lot_w = block / lots_x
    lot_d = block / lots_y

    for bc in range(cols):
        for br in range(rows):
            bx = street + bc * pitch
            by = street + br * pitch
            blocks.append({"col": bc, "row": br, "x_m": bx, "y_m": by, "size_m": block})
            for lx in range(lots_x):
                for ly in range(lots_y):
                    # density gates whether a lot is built
                    if rng.random() > density:
                        continue
                    cx = bx + (lx + 0.5) * lot_w
                    cy = by + (ly + 0.5) * lot_d
                    floors = int(rng.integers(fmin, fmax + 1))
                    var_seed = int(rng.integers(0, 2**31 - 1))
                    zone = _zone_for(rng)
                    fx, fy = round(lot_w * 0.85, 2), round(lot_d * 0.85, 2)
                    height = round(floors * fh, 2)
                    # taller toward block interior for cyberpunk/japan feel; gentle bias
                    instances.append({
                        "kit": f"{profile['streetNet']}_{zone}",   # kit variant id -> SM_<kit>.gltf
                        "x": round(cx * M, 1),
                        "y": round(cy * M, 1),
                        "z": 0.0,
                        "yaw": float(rng.choice([0.0, 90.0, 180.0, 270.0])),
                        "footprint_m": [fx, fy],
                        "floors": floors,
                        "height_m": height,
                        # unit-box (1 m) multiplier for HISM: [width, depth, height] in m
                        "scale3": [fx, fy, height],
                        "scale": 1.0,
                        "varSeed": var_seed,
                        "zone": zone,
                    })

    # --- road network: one slab instance per street segment (kit "road"). The slab
    # mesh runs along +X (length) × Z (width); yaw orients it, scale3 sizes it. ---
    road_instances: List[Dict[str, Any]] = []
    thick = 0.15
    for st in streets:
        if st["axis"] == "v":
            length = st["to_m"] - st["from_m"]
            cx, cy, yaw = st["x_m"], 0.5 * (st["from_m"] + st["to_m"]), 90.0
        else:
            length = st["to_m"] - st["from_m"]
            cx, cy, yaw = 0.5 * (st["from_m"] + st["to_m"]), st["y_m"], 0.0
        road_instances.append({
            "kit": "road", "x": round(cx * M, 1), "y": round(cy * M, 1), "z": 1.0,
            "yaw": yaw, "scale3": [round(length, 2), round(street, 2), thick], "scale": 1.0,
        })

    # --- props: the signature prop at intersections + street furniture along the
    # sidewalks at block spacing. Deterministic; capped. Each is a real-size proxy
    # (kit "prop_<kind>"), so scale3 is identity. ---
    kinds = list(profile["props"])
    prop_instances: List[Dict[str, Any]] = []

    def _add_prop(kind, x_m, y_m, yaw):
        prop_instances.append({"kit": f"prop_{kind}", "kind": kind,
                               "x": round(x_m * M, 1), "y": round(y_m * M, 1), "z": 0.0,
                               "yaw": float(yaw), "scale3": [1.0, 1.0, 1.0], "scale": 1.0})

    for c in range(cols + 1):
        for r in range(rows + 1):                       # signature prop at every corner
            _add_prop(kinds[0], c * pitch, r * pitch, rng.choice([0.0, 90.0, 180.0, 270.0]))
            props.append({"kind": kinds[0], "x": round(c * pitch * M, 1),
                          "y": round(r * pitch * M, 1), "z": 0.0})

    furniture = [k for k in kinds[1:3]] or kinds[:1]    # 1-2 street-furniture kinds
    off = street * 0.5 + 2.0                            # onto the sidewalk
    step = max(20.0, block * 0.5)
    for st in streets:
        n = int((st["to_m"] - st["from_m"]) // step)
        for i in range(1, n + 1):
            t = st["from_m"] + i * step
            kind = furniture[i % len(furniture)]
            if st["axis"] == "v":
                _add_prop(kind, st["x_m"] + off, t, 90.0)
            else:
                _add_prop(kind, t, st["y_m"] + off, 0.0)
            if len(prop_instances) > 600:
                break

    return {
        "schemaVersion": "psc.city.layout.v1",
        "streetNet": profile["streetNet"],
        "sizeBlocks": [cols, rows],
        "blockSizeM": block,
        "streetWidthM": street,
        "streets": streets,
        "blocks": blocks,
        "instances": instances,
        "road_instances": road_instances,
        "prop_instances": prop_instances,
        "props": props,
        "counts": {"instances": len(instances), "props": len(props), "blocks": len(blocks),
                   "roads": len(road_instances), "propInstances": len(prop_instances)},
    }

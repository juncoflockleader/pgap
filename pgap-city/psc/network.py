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

    # signature props at intersections (deterministic), capped
    prop_kind = profile["props"][0]
    for c in range(cols + 1):
        for r in range(rows + 1):
            props.append({
                "kind": prop_kind,
                "x": round(c * pitch * M, 1),
                "y": round(r * pitch * M, 1),
                "z": 0.0,
            })

    return {
        "schemaVersion": "psc.city.layout.v1",
        "streetNet": profile["streetNet"],
        "sizeBlocks": [cols, rows],
        "blockSizeM": block,
        "streetWidthM": street,
        "streets": streets,
        "blocks": blocks,
        "instances": instances,
        "props": props,
        "counts": {"instances": len(instances), "props": len(props), "blocks": len(blocks)},
    }

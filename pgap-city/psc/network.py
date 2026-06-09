"""Deterministic city layout grammar — per-style street networks.

Emits **instance transforms** (kit ref + position + rotation + scale + variation
seed + zone), not geometry — the bridge bulk-instances them (HISM). The street net
is chosen by the style profile and realized as a (possibly non-uniform) axis grid:

- **grid** (american): uniform big blocks, wide streets.
- **fine_grid** (japan): uniform small blocks, narrow streets — dense.
- **organic** (cyberpunk): jittered block sizes + **megablocks** (a block becomes one
  tall tower), height rising toward the core.
- **curved_industrial** (steampunk): jittered, larger irregular blocks.

(True curved/spline roads are a future refinement — see PRD open questions; v1 uses
irregular axis grids as the deterministic stand-in.) One seeded PCG64 throughout.
Units: centimeters (UE world units); Z=0 unless a terrain hook lifts it.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

M = 100.0  # meters -> cm


def _zone_for(rng: np.random.Generator) -> str:
    return str(rng.choice(["residential", "market", "civic"], p=[0.6, 0.3, 0.1]))


def _block_sizes(rng: np.random.Generator, n: int, base: float, net: str) -> List[float]:
    """Block sizes along one axis for the street net (deterministic)."""
    if net == "organic":
        return [round(base * (0.6 + 0.8 * rng.random()), 2) for _ in range(n)]   # ±
    if net == "curved_industrial":
        return [round(base * (0.78 + 0.55 * rng.random()), 2) for _ in range(n)]
    return [base] * n                                                            # grid / fine_grid


def _lines(block_sizes: List[float], sw: float):
    """Street centerlines + block spans (start,size) for one axis. The first street
    spans [0,sw]; centerlines sit between blocks; pitch = street + block (variable)."""
    centers = [sw / 2.0]
    spans = []
    pos = sw / 2.0
    for b in block_sizes:
        start = pos + sw / 2.0
        spans.append((start, b))
        pos = start + b + sw / 2.0
        centers.append(round(pos, 3))
    extent = round(pos + sw / 2.0, 3)
    return [round(c, 3) for c in centers], spans, extent


def generate_layout(profile: dict, size_blocks, seed: int, density: float) -> Dict[str, Any]:
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    cols, rows = int(size_blocks[0]), int(size_blocks[1])
    base = float(profile["blockSizeM"])
    street = float(profile["streetWidthM"])
    lots_x, lots_y = profile["lotsPerBlock"]
    fmin, fmax = profile["floors"]
    fh = float(profile["floorHeightM"])
    net = profile["streetNet"]

    bw_x = _block_sizes(rng, cols, base, net)
    bw_y = _block_sizes(rng, rows, base, net)
    xc, xspans, extent_x = _lines(bw_x, street)
    yc, yspans, extent_y = _lines(bw_y, street)

    streets: List[Dict[str, Any]] = []
    for x in xc:
        streets.append({"axis": "v", "x_m": x, "from_m": 0.0, "to_m": extent_y, "width_m": street})
    for y in yc:
        streets.append({"axis": "h", "y_m": y, "from_m": 0.0, "to_m": extent_x, "width_m": street})

    # organic cities grow tall toward the core (cyberpunk megablock skyline)
    cx0, cy0 = extent_x / 2.0, extent_y / 2.0
    rmax = (cx0 ** 2 + cy0 ** 2) ** 0.5 or 1.0
    mega = net == "organic"

    blocks: List[Dict[str, Any]] = []
    instances: List[Dict[str, Any]] = []
    props: List[Dict[str, Any]] = []

    def _floors(cxm, cym, boost=0.0):
        core = 1.0 - ((cxm - cx0) ** 2 + (cym - cy0) ** 2) ** 0.5 / rmax
        lo, hi = fmin, fmax
        if net in ("organic", "fine_grid"):
            lo = fmin + int((hi - fmin) * 0.45 * max(0.0, core))    # taller core
        return int(min(hi, rng.integers(lo, hi + 1) + boost))

    for bc, (bx, bwx) in enumerate(xspans):
        for br, (by, bwy) in enumerate(yspans):
            blocks.append({"col": bc, "row": br, "x_m": round(bx, 2), "y_m": round(by, 2),
                           "w_m": round(bwx, 2), "d_m": round(bwy, 2)})
            block_cx, block_cy = bx + bwx / 2.0, by + bwy / 2.0
            # megablock: one tall tower fills the block (cyberpunk)
            if mega and bwx > base * 0.8 and bwy > base * 0.8 and rng.random() < 0.28:
                if rng.random() <= density:
                    fl = _floors(block_cx, block_cy, boost=int((fmax - fmin) * 0.4))
                    instances.append(_inst(profile, block_cx, block_cy, bwx * 0.86, bwy * 0.86,
                                           fl, fh, "civic", rng, landmark=False))
                continue
            lw, ld = bwx / lots_x, bwy / lots_y
            for lx in range(lots_x):
                for ly in range(lots_y):
                    if rng.random() > density:
                        continue
                    cxm = bx + (lx + 0.5) * lw
                    cym = by + (ly + 0.5) * ld
                    zone = _zone_for(rng)
                    instances.append(_inst(profile, cxm, cym, lw * 0.85, ld * 0.85,
                                           _floors(cxm, cym), fh, zone, rng))

    layout = _finish(profile, [cols, rows], base, street, streets, blocks, instances,
                     props, xc, yc, extent_x, extent_y, rng, density)
    return layout


def _inst(profile, cxm, cym, fx, fy, floors, fh, zone, rng, landmark=False) -> Dict[str, Any]:
    fx, fy = round(fx, 2), round(fy, 2)
    height = round(floors * fh, 2)
    return {
        "kit": f"{profile['streetNet']}_{zone}",
        "x": round(cxm * M, 1), "y": round(cym * M, 1), "z": 0.0,
        "yaw": float(rng.choice([0.0, 90.0, 180.0, 270.0])),
        "footprint_m": [fx, fy], "floors": int(floors), "height_m": height,
        "scale3": [fx, fy, height], "scale": 1.0,
        "varSeed": int(rng.integers(0, 2**31 - 1)), "zone": zone,
        "landmark": bool(landmark),
    }


def _finish(profile, size_blocks, base, street, streets, blocks, instances, props,
            xc, yc, extent_x, extent_y, rng, density) -> Dict[str, Any]:
    cols, rows = size_blocks

    # roads: one slab per street segment (kit "road"); runs along +X, yaw orients it.
    road_instances: List[Dict[str, Any]] = []
    thick = 0.15
    for st in streets:
        length = st["to_m"] - st["from_m"]
        if st["axis"] == "v":
            cx, cy, yaw = st["x_m"], 0.5 * (st["from_m"] + st["to_m"]), 90.0
        else:
            cx, cy, yaw = 0.5 * (st["from_m"] + st["to_m"]), st["y_m"], 0.0
        road_instances.append({
            "kit": "road", "x": round(cx * M, 1), "y": round(cy * M, 1), "z": 1.0,
            "yaw": yaw, "scale3": [round(length, 2), round(st["width_m"], 2), thick], "scale": 1.0})

    # props: signature prop at intersections + street furniture along sidewalks.
    kinds = list(profile["props"])
    prop_instances: List[Dict[str, Any]] = []

    def _add_prop(kind, x_m, y_m, yaw):
        prop_instances.append({"kit": f"prop_{kind}", "kind": kind,
                               "x": round(x_m * M, 1), "y": round(y_m * M, 1), "z": 0.0,
                               "yaw": float(yaw), "scale3": [1.0, 1.0, 1.0], "scale": 1.0})

    for x in xc:
        for y in yc:
            _add_prop(kinds[0], x, y, rng.choice([0.0, 90.0, 180.0, 270.0]))
            props.append({"kind": kinds[0], "x": round(x * M, 1), "y": round(y * M, 1), "z": 0.0})

    furniture = kinds[1:3] or kinds[:1]
    off = street * 0.5 + 2.0
    step = max(20.0, base * 0.5)
    for st in streets:
        n = int((st["to_m"] - st["from_m"]) // step)
        for i in range(1, n + 1):
            kind = furniture[i % len(furniture)]
            if st["axis"] == "v":
                _add_prop(kind, st["x_m"] + off, st["from_m"] + i * step, 90.0)
            else:
                _add_prop(kind, st["from_m"] + i * step, st["y_m"] + off, 0.0)
            if len(prop_instances) > 600:
                break

    return {
        "schemaVersion": "psc.city.layout.v1",
        "streetNet": profile["streetNet"],
        "sizeBlocks": [cols, rows],
        "blockSizeM": base, "streetWidthM": street,
        "extentM": [round(extent_x, 2), round(extent_y, 2)],
        "streets": streets, "blocks": blocks, "instances": instances,
        "road_instances": road_instances, "prop_instances": prop_instances, "props": props,
        "counts": {"instances": len(instances), "props": len(props), "blocks": len(blocks),
                   "roads": len(road_instances), "propInstances": len(prop_instances),
                   "landmarks": sum(1 for i in instances if i.get("landmark"))},
    }

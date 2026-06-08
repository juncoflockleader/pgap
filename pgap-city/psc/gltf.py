"""Minimal glTF 2.0 writer for box-proxy building meshes (C0 kit).

A kit mesh is a **unit box** — x,y ∈ [-0.5, 0.5], z ∈ [0, 1] (XY-centered, sitting
on the ground) — with one PBR material. The city layout HISM-instances it with a
per-instance scale [footprint_x_m, footprint_y_m, height_m] and a ground position,
so a few meshes + a transform list build the whole skyline (PRD §5 instancing).

Self-contained (no Pillow/pygltf): geometry + a base64-embedded binary buffer in a
single .gltf. Deterministic — fixed bytes for fixed inputs.
"""

from __future__ import annotations

import base64
import json
from typing import Sequence

import numpy as np

# 8 corners of the unit box. glTF is Y-up, so the building's height is the Y axis
# (base at y=0, top at y=1) and the footprint is X×Z, both centered in [-0.5, 0.5].
# After the standard glTF->UE import (glTF Y -> UE Z), this lands upright with its
# base on the ground, and a per-instance scale [width, depth, height] maps to UE
# [X, Y, Z] cleanly.
_CORNERS = np.array([
    [-0.5, 0.0, -0.5], [0.5, 0.0, -0.5], [0.5, 0.0, 0.5], [-0.5, 0.0, 0.5],   # base (y=0)
    [-0.5, 1.0, -0.5], [0.5, 1.0, -0.5], [0.5, 1.0, 0.5], [-0.5, 1.0, 0.5],   # top  (y=1)
], dtype=np.float64)

# 6 faces as quads (corner indices); each becomes 2 triangles. Winding is corrected
# to face outward at build time, so the exact vertex order here need not be perfect.
_QUADS = [
    [0, 1, 2, 3],   # base
    [4, 5, 6, 7],   # top
    [0, 1, 5, 4],
    [1, 2, 6, 5],
    [2, 3, 7, 6],
    [3, 0, 4, 7],
]
_CENTER = np.array([0.0, 0.5, 0.0])


def _box_arrays():
    """Return (positions[N,3] f32, normals[N,3] f32, indices[M] u16) for the unit
    box with flat per-face normals and outward-facing winding."""
    pos, nrm, idx = [], [], []
    for quad in _QUADS:
        tris = [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]
        for tri in tris:
            v0, v1, v2 = (_CORNERS[i] for i in tri)
            n = np.cross(v1 - v0, v2 - v0)
            # flip winding so the geometric normal points away from the box center
            if np.dot(n, (v0 + v1 + v2) / 3.0 - _CENTER) < 0:
                tri = (tri[0], tri[2], tri[1])
                v1, v2 = v2, v1
                n = np.cross(v1 - v0, v2 - v0)
            n = n / (np.linalg.norm(n) + 1e-12)
            base = len(pos)
            for v in (v0, v1, v2):
                pos.append(v)
                nrm.append(n)
            idx.extend([base, base + 1, base + 2])
    return (np.array(pos, dtype=np.float32),
            np.array(nrm, dtype=np.float32),
            np.array(idx, dtype=np.uint16))


def box_gltf(color_rgb: Sequence[int], name: str = "Box") -> bytes:
    """A unit-box glTF (.gltf bytes) with baseColor = color_rgb (sRGB 0..255)."""
    pos, nrm, idx = _box_arrays()
    pos_b, nrm_b, idx_b = pos.tobytes(), nrm.tobytes(), idx.tobytes()
    # pad each section to 4-byte alignment
    def pad(b: bytes) -> bytes:
        return b + b"\x00" * (-len(b) % 4)
    pos_b, nrm_b, idx_b = pad(pos_b), pad(nrm_b), pad(idx_b)
    buf = pos_b + nrm_b + idx_b
    uri = "data:application/octet-stream;base64," + base64.b64encode(buf).decode("ascii")

    c = [round(float(x) / 255.0, 5) for x in color_rgb]
    gltf = {
        "asset": {"version": "2.0", "generator": "pgap-city psc"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "material": 0}]}],
        "materials": [{"name": name + "_mat", "pbrMetallicRoughness": {
            "baseColorFactor": [c[0], c[1], c[2], 1.0],
            "metallicFactor": 0.0, "roughnessFactor": 0.85}}],
        "buffers": [{"byteLength": len(buf), "uri": uri}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b), "byteLength": len(nrm_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b) + len(nrm_b), "byteLength": len(idx_b),
             "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": int(len(pos)), "type": "VEC3",
             "min": [-0.5, 0.0, -0.5], "max": [0.5, 1.0, 0.5]},
            {"bufferView": 1, "componentType": 5126, "count": int(len(nrm)), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5123, "count": int(len(idx)), "type": "SCALAR"},
        ],
    }
    return json.dumps(gltf, indent=2).encode("utf-8")

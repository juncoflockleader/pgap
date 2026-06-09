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


def _uv_for(v: np.ndarray, n: np.ndarray) -> tuple:
    """UV for a box vertex: walls map U=horizontal, V=height (base→bottom of image so
    the ground floor lands at the building base); top/base map the footprint."""
    ax = int(np.argmax(np.abs(n)))
    if ax == 1:                       # top / base face → footprint (X,Z)
        return (v[0] + 0.5, v[2] + 0.5)
    if ax == 0:                       # ±X wall → U=Z, V=height (flipped)
        return (v[2] + 0.5, 1.0 - v[1])
    return (v[0] + 0.5, 1.0 - v[1])   # ±Z wall → U=X, V=height (flipped)


def _box_arrays_uv():
    """Box arrays with flat normals + UVs, and a split of triangles into wall vs roof
    (the top face) so each gets its own material. Returns (pos, nrm, uv, wall_idx,
    roof_idx)."""
    pos, nrm, uv, wall_idx, roof_idx = [], [], [], [], []
    for face, quad in enumerate(_QUADS):
        is_top = (face == 1)          # _QUADS[1] is the top (y=1) face
        for tri in [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]:
            v0, v1, v2 = (_CORNERS[i] for i in tri)
            n = np.cross(v1 - v0, v2 - v0)
            if np.dot(n, (v0 + v1 + v2) / 3.0 - _CENTER) < 0:
                tri = (tri[0], tri[2], tri[1])
                v0, v1, v2 = _CORNERS[tri[0]], _CORNERS[tri[1]], _CORNERS[tri[2]]
                n = np.cross(v1 - v0, v2 - v0)
            n = n / (np.linalg.norm(n) + 1e-12)
            base = len(pos)
            for v in (v0, v1, v2):
                pos.append(v)
                nrm.append(n)
                uv.append(_uv_for(v, n))
            (roof_idx if is_top else wall_idx).extend([base, base + 1, base + 2])
    return (np.array(pos, dtype=np.float32), np.array(nrm, dtype=np.float32),
            np.array(uv, dtype=np.float32), np.array(wall_idx, dtype=np.uint16),
            np.array(roof_idx, dtype=np.uint16))


def building_gltf(wall_base: bytes, wall_normal: bytes, roof_base: bytes,
                  roof_normal: bytes, *, wall_emissive: bytes | None = None,
                  emissive_factor: Sequence[float] = (1.0, 1.0, 1.0),
                  metallic: float = 0.0, roughness: float = 0.85,
                  name: str = "Building") -> bytes:
    """A unit-box building skinned with facade (walls) + roof textures (PNG bytes),
    embedded. Two primitives/materials: walls get base+normal(+emissive), the top
    gets the roof base+normal. Wraps REPEAT; deterministic for fixed inputs."""
    pos, nrm, uv, wall_idx, roof_idx = _box_arrays_uv()

    def pad(b: bytes) -> bytes:
        return b + b"\x00" * (-len(b) % 4)

    # assemble the binary buffer: geometry, then index sets, then PNG images
    blob = bytearray()
    views = []  # (byteOffset, byteLength, target_or_None)

    def add(data: bytes, target=None) -> int:
        data = pad(data)
        off = len(blob)
        blob.extend(data)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data),
                      **({"target": target} if target else {})})
        return len(views) - 1

    v_pos = add(pos.tobytes(), 34962)
    v_nrm = add(nrm.tobytes(), 34962)
    v_uv = add(uv.tobytes(), 34962)
    v_wall = add(wall_idx.tobytes(), 34963)
    v_roof = add(roof_idx.tobytes(), 34963)

    pngs = [wall_base, wall_normal, roof_base, roof_normal]
    if wall_emissive is not None:
        pngs.append(wall_emissive)
    img_views = [add(p) for p in pngs]  # raw PNG byteviews (no target)

    accessors = [
        {"bufferView": v_pos, "componentType": 5126, "count": int(len(pos)), "type": "VEC3",
         "min": [-0.5, 0.0, -0.5], "max": [0.5, 1.0, 0.5]},
        {"bufferView": v_nrm, "componentType": 5126, "count": int(len(nrm)), "type": "VEC3"},
        {"bufferView": v_uv, "componentType": 5126, "count": int(len(uv)), "type": "VEC2"},
        {"bufferView": v_wall, "componentType": 5123, "count": int(len(wall_idx)), "type": "SCALAR"},
        {"bufferView": v_roof, "componentType": 5123, "count": int(len(roof_idx)), "type": "SCALAR"},
    ]
    a_pos, a_nrm, a_uv, a_wall, a_roof = 0, 1, 2, 3, 4   # accessor indices (order above)
    images = [{"bufferView": iv, "mimeType": "image/png"} for iv in img_views]
    textures = [{"source": i, "sampler": 0} for i in range(len(images))]

    wall_mat = {
        "name": name + "_facade",
        "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicFactor": metallic, "roughnessFactor": roughness},
        "normalTexture": {"index": 1},
    }
    if wall_emissive is not None:
        wall_mat["emissiveTexture"] = {"index": 4}
        wall_mat["emissiveFactor"] = [round(float(x), 4) for x in emissive_factor]
    roof_mat = {
        "name": name + "_roof",
        "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 2},
            "metallicFactor": metallic, "roughnessFactor": min(1.0, roughness + 0.05)},
        "normalTexture": {"index": 3},
    }

    uri = "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode("ascii")
    gltf = {
        "asset": {"version": "2.0", "generator": "pgap-city psc"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": [
            {"attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv},
             "indices": a_wall, "material": 0},
            {"attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv},
             "indices": a_roof, "material": 1},
        ]}],
        "materials": [wall_mat, roof_mat],
        "samplers": [{"wrapS": 10497, "wrapT": 10497}],  # REPEAT
        "images": images,
        "textures": textures,
        "buffers": [{"byteLength": len(blob), "uri": uri}],
        "bufferViews": views,
        "accessors": accessors,
    }
    return json.dumps(gltf, indent=2).encode("utf-8")


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

"""Minimal multi-material static-mesh glTF 2.0 writer (no skin, no textures).

Triangles are grouped by their material name into one primitive each; every
material is a flat PBR (baseColorFactor + metallic + roughness from the gear
material library). Self-contained: a single base64-embedded buffer. Deterministic.
"""

from __future__ import annotations

import base64
import json
from typing import List

import numpy as np

from .materials import factors


def gear_gltf(pos: np.ndarray, nrm: np.ndarray, idx: np.ndarray,
              tri_mat: List[str], name: str = "Gear") -> bytes:
    pos = np.ascontiguousarray(pos, dtype=np.float32)
    nrm = np.ascontiguousarray(nrm, dtype=np.float32)
    tris = idx.reshape(-1, 3)
    mats = sorted(set(tri_mat))                       # stable material order

    blob = bytearray()
    views = []

    def add(data: bytes, target=None) -> int:
        data = data + b"\x00" * (-len(data) % 4)
        off = len(blob)
        blob.extend(data)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data),
                      **({"target": target} if target else {})})
        return len(views) - 1

    v_pos = add(pos.tobytes(), 34962)
    v_nrm = add(nrm.tobytes(), 34962)
    accessors = [
        {"bufferView": v_pos, "componentType": 5126, "count": int(len(pos)), "type": "VEC3",
         "min": [float(pos[:, i].min()) for i in range(3)],
         "max": [float(pos[:, i].max()) for i in range(3)]},
        {"bufferView": v_nrm, "componentType": 5126, "count": int(len(nrm)), "type": "VEC3"},
    ]
    tri_mat_arr = np.asarray(tri_mat)
    primitives, materials = [], []
    for mi, mname in enumerate(mats):
        sel = tris[tri_mat_arr == mname].reshape(-1).astype(np.uint32)
        v_idx = add(sel.tobytes(), 34963)
        a_idx = len(accessors)
        accessors.append({"bufferView": v_idx, "componentType": 5125,
                          "count": int(len(sel)), "type": "SCALAR"})
        primitives.append({"attributes": {"POSITION": 0, "NORMAL": 1},
                           "indices": a_idx, "material": mi})
        materials.append({"name": mname, "pbrMetallicRoughness": {
            "baseColorFactor": factors(mname)["baseColorFactor"],
            "metallicFactor": factors(mname)["metallicFactor"],
            "roughnessFactor": factors(mname)["roughnessFactor"]}})

    uri = "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode("ascii")
    gltf = {
        "asset": {"version": "2.0", "generator": "pgap-gear pgear"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": primitives}],
        "materials": materials,
        "buffers": [{"byteLength": len(blob), "uri": uri}],
        "bufferViews": views, "accessors": accessors,
    }
    return json.dumps(gltf, indent=2).encode("utf-8")

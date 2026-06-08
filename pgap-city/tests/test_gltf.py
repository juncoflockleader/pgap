"""C0 building kit: box-proxy glTF meshes + instance HISM contract."""

from __future__ import annotations

import base64
import json

import numpy as np

from psc import generate
from psc.gltf import box_gltf


def _decode(g, view):
    raw = base64.b64decode(g["buffers"][0]["uri"].split(",", 1)[1])
    bv = g["bufferViews"][view]
    seg = raw[bv["byteOffset"]: bv["byteOffset"] + bv["byteLength"]]
    return seg


def test_box_is_valid_unit_gltf():
    g = json.loads(box_gltf((120, 90, 60)))
    assert g["asset"]["version"] == "2.0"
    pos = np.frombuffer(_decode(g, 0), dtype="<f4").reshape(-1, 3)
    idx = np.frombuffer(_decode(g, 2), dtype="<u2")
    assert len(pos) == 36 and len(idx) == 36          # 12 tris, flat-shaded
    assert idx.max() < len(pos)
    assert np.allclose(pos.min(0), [-0.5, 0.0, -0.5])  # Y-up unit box, base at y=0
    assert np.allclose(pos.max(0), [0.5, 1.0, 0.5])


def test_normals_are_unit_and_outward():
    g = json.loads(box_gltf((120, 90, 60)))
    pos = np.frombuffer(_decode(g, 0), dtype="<f4").reshape(-1, 3)
    nrm = np.frombuffer(_decode(g, 1), dtype="<f4").reshape(-1, 3)
    assert np.allclose(np.linalg.norm(nrm, axis=1), 1.0, atol=1e-3)
    center = np.array([0.0, 0.5, 0.0])
    # each vertex normal points away from the box center
    assert np.all(np.sum(nrm * (pos - center), axis=1) > 0)


def test_basecolor_matches_and_deterministic():
    a = box_gltf((200, 100, 50))
    b = box_gltf((200, 100, 50))
    assert a == b                                      # byte-identical
    g = json.loads(a)
    bc = g["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
    assert abs(bc[0] - 200 / 255) < 1e-3 and bc[3] == 1.0


def test_pipeline_emits_one_mesh_per_kit(tmp_path):
    m, paths = generate({"name": "C", "era": "modern", "culture": "american",
                         "seed": 5, "sizeBlocks": [4, 4]}, tmp_path, handoff=True)
    layout = json.loads(paths["layout"].read_text())
    kit_ids = {k["id"] for k in layout["kits"]}
    assert kit_ids and m["counts"]["kits"] == len(kit_ids)
    for kit in kit_ids:
        assert (tmp_path / f"SM_{kit}.gltf").exists()
        assert f"BuildingKit:{kit}" in m["roles"]
        assert f"SM_{kit}.gltf" in m["files"]
    # every instance references a real kit + carries a 3-axis HISM scale
    for inst in layout["instances"]:
        assert inst["kit"] in kit_ids
        assert len(inst["scale3"]) == 3 and inst["scale3"][2] > 0
    # handoff lists the BuildingKit roles
    hand = json.loads(paths["handoff"].read_text())
    assert any(r["role"].startswith("BuildingKit:") for r in hand["roles"])

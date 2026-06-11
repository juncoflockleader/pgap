"""Geometry kernel + every template/variant builds a valid multi-material mesh."""

import json

import numpy as np

from pgear import gltf, materials, render
from pgear.geom import MeshBuilder
from pgear.items import _blade
from pgear.registry import TEMPLATES


def _mesh(template, variant=None, mat=""):
    t = TEMPLATES[template]
    ms = materials.resolve_materials(mat, t["mats"]["metal"], t["mats"]["grip"], t["mats"]["accent"])
    mb = MeshBuilder()
    sockets = t["fn"](mb, ms, 1.0, variant or t["variants"][0])
    return mb.build(), sockets


def test_every_template_builds_valid():
    for name in TEMPLATES:
        (pos, nrm, idx, tri_mat), _ = _mesh(name)
        assert len(idx) > 0 and len(idx) % 3 == 0, name
        assert np.isfinite(pos).all() and np.isfinite(nrm).all(), name
        assert np.allclose(np.linalg.norm(nrm, axis=1), 1.0, atol=1e-3), name   # unit normals
        assert len(tri_mat) == len(idx) // 3 and all(tri_mat), name             # every tri tagged
        assert len(idx) // 3 <= 4000, name                                      # tri budget


def test_every_variant_builds():
    for name, t in TEMPLATES.items():
        for v in t["variants"]:
            (pos, nrm, idx, tm), _ = _mesh(name, v)
            assert len(idx) > 0, (name, v)


def test_socket_grip_present():
    for name in TEMPLATES:
        _, sockets = _mesh(name)
        assert "grip" in sockets


def test_curved_blade_segments_share_boundaries():
    mb = MeshBuilder()
    _blade(mb, {"metal": "steel"}, 0.0, 1.0, 0.10, 0.02, curve=0.18)
    pos, _, _, _ = mb.build()
    ys = sorted({round(float(y), 6) for y in pos[:, 1]})
    for y in ys[1:-1]:
        xs = sorted({round(float(p[0]), 6) for p in pos if round(float(p[1]), 6) == y})
        assert len(xs) == 2


def test_gltf_is_multi_material_and_valid():
    (pos, nrm, idx, tri_mat), _ = _mesh("sword", mat="iron leather gold")
    g = json.loads(gltf.gear_gltf(pos, nrm, idx, tri_mat, name="SM_t"))
    prims = g["meshes"][0]["primitives"]
    assert len(prims) == len(g["materials"]) == len(set(tri_mat))
    assert all("POSITION" in p["attributes"] and "NORMAL" in p["attributes"] for p in prims)
    # index counts across primitives sum to the triangle soup
    total = sum(g["accessors"][p["indices"]]["count"] for p in prims)
    assert total == len(idx)
    # iron blade + gold accent both present as named materials
    names = {m["name"] for m in g["materials"]}
    assert "iron" in names and "gold" in names


def test_render_is_nonempty_and_deterministic():
    (pos, nrm, idx, tm), _ = _mesh("axe")
    a = render.render_image(pos, nrm, idx, tm, size=64)
    b = render.render_image(pos, nrm, idx, tm, size=64)
    assert a.shape == (64, 64, 3) and a.dtype == np.uint8
    assert np.array_equal(a, b)
    bg = a[0, 0].astype(int)
    assert (np.abs(a.astype(int) - bg).sum(2) > 10).mean() > 0.01           # the gear is drawn

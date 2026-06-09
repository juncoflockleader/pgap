"""Roadmap 4 — part proportions (girth). Girth scales part *thickness* (radius)
only: the mesh gets stockier/leaner while the rig, skin weights, and clips stay
byte-identical (purely a surface knob, orthogonal to heightCm)."""

import json
from pathlib import Path

import numpy as np

from pgap.pipeline import build_actor as v1_build_actor
from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.animate import animate_recipe
from pgap.v2.assembly import build_actor
from pgap.v2.nl import prompt_to_recipe
from pgap.v2.recipe import recipe_from_dict, validate_recipe
from pgap.v2.registry import build_module, load_template

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _spec(girth=1.0, h=120):
    return Spec.from_dict({"name": "g", "archetype": "biped", "species": "g", "seed": 5,
                           "triBudget": 11000, "proportions": {"heightCm": h, "girth": girth},
                           "material": {"baseColor": "tan"}})


def _z_extent(mesh):
    """Width (Z span) of the mid-height slab — a proxy for build/thickness."""
    p = mesh.positions
    ymid = 0.5 * (p[:, 1].min() + p[:, 1].max())
    band = p[np.abs(p[:, 1] - ymid) < 0.12]
    return float(band[:, 2].max() - band[:, 2].min())


def test_spec_girth_is_clamped():
    assert _spec(5.0).girth == 1.6 and _spec(0.1).girth == 0.6 and _spec(1.0).girth == 1.0


def test_girth_thickens_the_mesh_but_not_the_rig():
    rec = load_template("biped")
    sk_lean, m_lean = build_actor(rec, _spec(0.7), make_rng(5))
    sk_fat, m_fat = build_actor(rec, _spec(1.4), make_rng(5))
    assert _z_extent(m_fat) > _z_extent(m_lean) * 1.1            # visibly stockier
    # the rig is byte-identical — girth is purely the SDF surface
    for a, b in zip(sk_lean, sk_fat):
        assert a.parent == b.parent
        assert np.array_equal(a.head, b.head) and np.array_equal(a.tail, b.tail)
    assert any(abs(a.radius_head - b.radius_head) > 1e-6 for a, b in zip(sk_lean, sk_fat))


def test_girth_leaves_clips_identical_and_weights_valid():
    # The mesh changes (fatter ⇒ different marching-cubes verts), so per-vertex
    # weights differ — but the *clips* (joint rotations) are mesh-independent and
    # must be byte-identical, and skinning stays valid at any build.
    rec = load_template("wolf")
    _, m0 = build_actor(rec, _spec(1.0), make_rng(5))
    _, m1 = build_actor(rec, _spec(1.5), make_rng(5))
    for m in (m0, m1):
        assert np.allclose(m.weights.sum(axis=1), 1.0, atol=1e-5)
        assert m.weights.shape[1] == 4
    c0 = animate_recipe(rec, _spec(1.0))
    c1 = animate_recipe(rec, _spec(1.5))
    assert [c.name for c in c0] == [c.name for c in c1]
    for a, b in zip(c0, c1):
        assert [ch.bone for ch in a.channels] == [ch.bone for ch in b.channels]
        for ca, cb in zip(a.channels, b.channels):
            assert np.array_equal(ca.values, cb.values)       # rotations don't depend on girth


def test_girth_is_deterministic():
    a = build_actor(load_template("biped"), _spec(1.3), make_rng(5))[1]
    b = build_actor(load_template("biped"), _spec(1.3), make_rng(5))[1]
    assert np.array_equal(a.positions, b.positions)


def test_per_part_girth_thickens_only_that_part():
    base = build_module("leg").bones[0].radius_head
    assert abs(build_module("leg", params={"girth": 1.5}).bones[0].radius_head - base * 1.5) < 1e-9
    data = {"name": "B", "modules": [
        {"id": "spine", "kind": "spine"},
        {"id": "head", "kind": "head", "attach": "spine.neck"},
        {"id": "leg", "kind": "leg", "attach": "spine.hip", "mirror": True, "params": {"girth": 1.6}}]}
    assert validate_recipe(data)["ok"]                          # girth accepted on any kind
    skel, _ = build_actor(recipe_from_dict(data), _spec(1.0), make_rng(5))
    thigh = next(b for b in skel if b.name == "leg_l_thigh")
    assert thigh.radius_head > base * (120 / 60) * 1.4          # a clearly chubbier leg


def test_v1_girth_thickens_the_dog_without_moving_bones():
    data = json.loads((FIX / "dog_golden_retriever.json").read_text())

    def dog(girth):
        d = dict(data)
        d["proportions"] = {**data.get("proportions", {}), "girth": girth}
        spec = Spec.from_dict(d)
        return v1_build_actor(spec, make_rng(spec.seed))

    sk0, m0 = dog(0.75)
    sk1, m1 = dog(1.4)
    assert _z_extent(m1) > _z_extent(m0)
    for a, b in zip(sk0, sk1):
        assert np.array_equal(a.head, b.head) and np.array_equal(a.tail, b.tail)


def test_nl_routes_girth():
    assert prompt_to_recipe("a stocky dragon", mode="strict")["girth"] == 1.35
    assert prompt_to_recipe("a lanky knight", mode="strict")["girth"] == 0.7
    free = prompt_to_recipe("a beast with chubby legs", mode="free")["recipe_dict"]
    legs = [m for m in free["modules"] if m["id"] in ("foreleg", "hindleg", "leg")]
    assert legs and all(m["params"]["girth"] > 1.0 for m in legs)

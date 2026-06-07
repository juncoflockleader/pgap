"""V3-M5: variant corpus — every variant of every slot, and every template,
builds valid, non-degenerate, within budget, and deterministic.

The regression gate that locks in the whole v2/v3 module + variant system.
"""

from __future__ import annotations

import hashlib

import numpy as np

from pgap.assemble import assemble_gltf
from pgap.geometry import mesh_stats
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec
from pgap.v2.animate import animate_recipe
from pgap.v2.assembly import build_actor
from pgap.v2.recipe import recipe_from_dict
from pgap.v2.registry import MODULE_REGISTRY, TEMPLATE_HEIGHT_CM, TEMPLATE_REGISTRY, load_template


def _spec(name, seed=5, budget=11000, h=120):
    return Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": seed,
                           "triBudget": budget, "proportions": {"heightCm": h},
                           "material": {"baseColor": "stone"}})


def _assert_valid(mesh, spec, tag):
    st = mesh_stats(mesh)
    assert st["triangles"] > 0 and st["finite"], tag
    assert mesh.num_triangles <= spec.tri_budget, tag
    assert st["boundary_edges"] < 0.03 * st["triangles"] * 3, tag
    assert st["nonmanifold_edges"] < 0.03 * st["triangles"] * 3, tag
    if mesh.weights is not None:
        assert skin_stats(mesh)["unweighted_vertices"] == 0, tag
        assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5), tag


def test_every_module_variant_builds_in_isolation():
    for kind, mk in MODULE_REGISTRY.items():
        for variant in mk.variants:
            spec = _spec(f"{kind}_{variant}", budget=8000, h=80)
            recipe = recipe_from_dict({"name": kind, "modules": [
                {"id": "m", "kind": kind, "variant": variant}]})
            _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
            _assert_valid(mesh, spec, (kind, variant))


def test_head_part_variants_compose_on_a_host():
    # horns / ears / tusks of every variant, on a real body+neck+head creature.
    slots = {"horn": "head.horns", "ear": "head.ears", "tusk": "head.tusks"}
    for kind, attach in slots.items():
        for variant in MODULE_REGISTRY[kind].variants:
            spec = _spec(f"host_{kind}_{variant}")
            recipe = recipe_from_dict({"name": "Host", "modules": [
                {"id": "body", "kind": "body"},
                {"id": "neck", "kind": "neck", "attach": "body.neck"},
                {"id": "head", "kind": "head", "attach": "neck.top"},
                {"id": "part", "kind": kind, "variant": variant, "attach": attach},
                {"id": "leg", "kind": "leg", "attach": "body.shoulder", "mirror": True}]})
            _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
            _assert_valid(mesh, spec, (kind, variant))


def test_wing_variants_compose_on_a_body():
    for variant in MODULE_REGISTRY["wing"].variants:
        spec = _spec(f"wing_{variant}")
        recipe = recipe_from_dict({"name": "W", "modules": [
            {"id": "body", "kind": "body"},
            {"id": "wing", "kind": "wing", "variant": variant, "attach": "body.wings", "mirror": True}]})
        _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
        _assert_valid(mesh, spec, ("wing", variant))


def test_all_templates_build_within_budget():
    for name in TEMPLATE_REGISTRY:
        spec = _spec(name, h=TEMPLATE_HEIGHT_CM[name])
        skel, mesh = build_actor(load_template(name), spec, make_rng(spec.seed))
        _assert_valid(mesh, spec, name)
        assert len(skel) >= 1


def test_templates_deterministic_per_seed():
    def sha(name):
        spec = _spec(name, h=TEMPLATE_HEIGHT_CM[name])
        skel, mesh = build_actor(load_template(name), spec, make_rng(spec.seed))
        clips = animate_recipe(load_template(name), spec)
        return hashlib.sha1(assemble_gltf(mesh, name, skel, clips)).hexdigest()

    for name in ("dragon", "beholder", "unicorn", "horse"):
        assert sha(name) == sha(name), name

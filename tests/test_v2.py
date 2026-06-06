"""V2-M0: the module/socket core assembles a valid skinned biped from a recipe."""

from __future__ import annotations

import hashlib

import numpy as np

from pgap.assemble import assemble_gltf
from pgap.geometry import mesh_stats
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec
from pgap.v2.assembly import assemble_recipe, build_actor
from pgap.v2.library import biped_recipe


def _spec():
    return Spec.from_dict({
        "name": "ModularBiped", "archetype": "biped", "species": "humanoid",
        "seed": 3, "triBudget": 8000, "proportions": {"heightCm": 180},
        "material": {"baseColor": "tan"},
    })


def test_recipe_assembles_expected_bones():
    skel = assemble_recipe(biped_recipe(), _spec())
    names = [b.name for b in skel]
    # spine(3) + neck(1) + head(1) + arm x2 (3) + leg x2 (3) = 17
    assert len(skel) == 17
    assert len(set(names)) == 17  # unique
    assert skel[0].name == "spine_root" and skel[0].parent is None
    assert {"arm_l_upperarm", "arm_r_upperarm", "leg_l_thigh", "leg_r_thigh"} <= set(names)


def test_all_parents_resolve():
    skel = assemble_recipe(biped_recipe(), _spec())
    names = {b.name for b in skel}
    for b in skel:
        assert b.parent is None or b.parent in names, b.name


def test_mirror_reflects_z():
    skel = {b.name: b for b in assemble_recipe(biped_recipe(), _spec())}
    assert skel["arm_l_upperarm"].head[2] > 0
    assert skel["arm_r_upperarm"].head[2] < 0
    # mirror is a clean reflection
    assert np.isclose(skel["arm_l_upperarm"].head[2], -skel["arm_r_upperarm"].head[2])


def test_build_produces_valid_skinned_mesh():
    spec = _spec()
    skel, mesh = build_actor(biped_recipe(), spec, make_rng(spec.seed))
    st = mesh_stats(mesh)
    assert st["triangles"] > 0 and st["finite"]
    assert mesh.num_triangles <= spec.tri_budget
    edges = st["triangles"] * 3
    assert st["boundary_edges"] < 0.02 * edges
    ss = skin_stats(mesh)
    assert ss["unweighted_vertices"] == 0
    assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5)


def test_v2_deterministic():
    spec = _spec()

    def sha():
        skel, mesh = build_actor(biped_recipe(), spec, make_rng(spec.seed))
        return hashlib.sha1(assemble_gltf(mesh, spec.name, skel)).hexdigest()

    assert sha() == sha()

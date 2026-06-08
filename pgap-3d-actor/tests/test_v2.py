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
from pgap.v2.library import (
    Attachment, beholder_recipe, biped_recipe, fin_module, kraken_recipe,
    merfolk_recipe, octopus_dragon_recipe, orb_module, sphinx_recipe,
    tentacle_module, wing_module,
)
from pgap.v2.types import Recipe


def _spec():
    return Spec.from_dict({
        "name": "ModularBiped", "archetype": "biped", "species": "humanoid",
        "seed": 3, "triBudget": 8000, "proportions": {"heightCm": 180},
        "material": {"baseColor": "tan"},
    })


def test_recipe_assembles_expected_bones():
    skel = assemble_recipe(biped_recipe(), _spec())
    names = [b.name for b in skel]
    # spine(3) + neck(1) + head(1) + eyes(2) + jaws(2) + arm x2 (3) + leg x2 (3) = 21
    assert len(skel) == 21
    assert len(set(names)) == 21  # unique
    assert skel[0].name == "spine_root" and skel[0].parent is None
    assert {"arm_l_upperarm", "arm_r_upperarm", "leg_l_thigh", "leg_r_thigh"} <= set(names)
    assert {"eyes_eye_l", "eyes_eye_r"} <= set(names)   # a mirrored eye pair
    assert {"jaws_nose", "jaws_mouth"} <= set(names)    # a nose + mouth line


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


# --- V2-M1: chain modules + radial (ring) sockets -------------------------- #
def _creature_spec(name, height=80, budget=9000):
    return Spec.from_dict({
        "name": name, "archetype": "biped", "species": name.lower(), "seed": 5,
        "triBudget": budget, "proportions": {"heightCm": height},
        "material": {"baseColor": "purple"},
    })


def test_ring_expands_to_n_instances():
    skel = assemble_recipe(beholder_recipe(eyes=8), _creature_spec("Beholder"))
    names = [b.name for b in skel]
    # orb(1) + central eye(1) + 8 eyestalks x 3 bones = 26
    assert len(skel) == 26
    stalk_eyes = [n for n in names if n.startswith("stalk_") and n.endswith("_eye")]
    assert len(stalk_eyes) == 8  # one eyeball per ring instance


def test_ring_instances_are_rotated_around_the_circle():
    skel = {b.name: b for b in assemble_recipe(beholder_recipe(eyes=8), _creature_spec("Beholder"))}
    import numpy as np
    # Eyestalk tips fan out radially → distinct XZ positions, all off-axis.
    p0 = skel["stalk_0_eye"].head
    p2 = skel["stalk_2_eye"].head
    assert not np.allclose(p0[[0, 2]], p2[[0, 2]])
    radii = [np.hypot(skel[f"stalk_{k}_eye"].head[0], skel[f"stalk_{k}_eye"].head[2]) for k in range(8)]
    assert min(radii) > 0.05  # genuinely splayed out, not stacked on the axis


def test_single_modules_build_in_isolation():
    # V2-M1 exit: each module meshes + skins on its own.
    for rec in (Recipe("OrbOnly", [Attachment("orb", orb_module())]),
                Recipe("TentacleOnly", [Attachment("t", tentacle_module())])):
        spec = _creature_spec(rec.name, budget=6000)
        skel, mesh = build_actor(rec, spec, make_rng(spec.seed))
        assert mesh.num_triangles > 0 and mesh.weights is not None
        assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5)


def test_chimera_recipes_are_valid():
    for rec, h in ((beholder_recipe(), 80), (kraken_recipe(), 70)):
        spec = _creature_spec(rec.name, height=h)
        skel, mesh = build_actor(rec, spec, make_rng(spec.seed))
        st = mesh_stats(mesh)
        assert st["finite"] and st["triangles"] > 0
        assert mesh.num_triangles <= spec.tri_budget
        assert st["boundary_edges"] < 0.02 * st["triangles"] * 3
        assert skin_stats(mesh)["unweighted_vertices"] == 0


def test_chimera_deterministic():
    spec = _creature_spec("Beholder")

    def sha():
        skel, mesh = build_actor(beholder_recipe(), spec, make_rng(spec.seed))
        return hashlib.sha1(assemble_gltf(mesh, spec.name, skel)).hexdigest()

    assert sha() == sha()


# --- V2-M1 (cont.): wing/fin/head-variant chimeras ------------------------- #
def test_wing_and_fin_modules_build_in_isolation():
    for rec in (Recipe("WingOnly", [Attachment("w", wing_module())]),
                Recipe("FinOnly", [Attachment("f", fin_module())])):
        spec = _creature_spec(rec.name, budget=6000)
        _, mesh = build_actor(rec, spec, make_rng(spec.seed))
        assert mesh.num_triangles > 0
        assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5)


def test_full_chimera_recipes_are_valid():
    recipes = {
        "OctopusDragon": (octopus_dragon_recipe(), 130),
        "Sphinx": (sphinx_recipe(), 120),
        "Merfolk": (merfolk_recipe(), 175),
    }
    for name, (rec, h) in recipes.items():
        spec = _creature_spec(name, height=h, budget=10000)
        skel, mesh = build_actor(rec, spec, make_rng(spec.seed))
        st = mesh_stats(mesh)
        assert st["finite"] and st["triangles"] > 0, name
        assert mesh.num_triangles <= spec.tri_budget, name
        assert st["boundary_edges"] < 0.02 * st["triangles"] * 3, name
        assert skin_stats(mesh)["unweighted_vertices"] == 0, name
        # composite creatures pull in many module types
        assert len(skel) >= 20, name

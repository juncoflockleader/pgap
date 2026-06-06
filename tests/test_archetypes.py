"""M6: prop (rigless static) and biped (skeleton-first) archetype routing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from pgap.animation import animate
from pgap.assemble import assemble_gltf
from pgap.pipeline import build_actor, build_bundle
from pgap.rng import make_rng
from pgap.skeleton import BIPED_BONE_NAMES, build_skeleton
from pgap.skinning import skin_stats
from pgap.spec import Spec

FIX = Path(__file__).resolve().parents[1] / "fixtures"
PROP = FIX / "prop_rock.json"
BIPED = FIX / "biped_simple.json"


# --- prop fast path -------------------------------------------------------- #
def test_prop_has_no_skeleton_or_skin():
    spec = Spec.load(PROP)
    skel, mesh = build_actor(spec, make_rng(spec.seed))
    assert skel == []
    assert mesh.joints is None and mesh.weights is None
    assert mesh.num_triangles > 0 and np.isfinite(mesh.positions).all()


def test_prop_within_budget_and_has_uvs():
    spec = Spec.load(PROP)
    _, mesh = build_actor(spec, make_rng(spec.seed))
    assert mesh.num_triangles <= spec.tri_budget
    assert mesh.uvs is not None


def test_prop_gltf_is_static_no_skin():
    import json
    spec = Spec.load(PROP)
    skel, mesh, clips, textures = build_bundle(spec, make_rng(spec.seed))
    assert clips == []
    doc = json.loads(assemble_gltf(mesh, spec.name, skel or None, clips, textures))
    assert "skins" not in doc
    assert doc["meshes"][0]["primitives"][0].get("material") == 0  # textured


def test_prop_deterministic():
    spec = Spec.load(PROP)

    def sha():
        skel, mesh, clips, tex = build_bundle(spec, make_rng(spec.seed))
        return hashlib.sha1(assemble_gltf(mesh, spec.name, skel or None, clips, tex)).hexdigest()

    assert sha() == sha()


# --- biped skeleton-first -------------------------------------------------- #
def test_biped_rig_and_weights():
    spec = Spec.load(BIPED)
    skel, mesh = build_actor(spec, make_rng(spec.seed))
    assert tuple(b.name for b in skel) == BIPED_BONE_NAMES
    assert len(skel) == 17
    sums = mesh.weights.sum(axis=1)
    assert np.allclose(sums, 1.0, atol=1e-5)
    assert skin_stats(mesh)["unweighted_vertices"] == 0


def test_biped_clips_are_biped_specific():
    spec = Spec.load(BIPED)
    skel = build_skeleton(spec, make_rng(spec.seed))
    clips = {c.name for c in animate(skel, spec)}
    assert clips == {"idle", "walk"}  # tail_wag/bark_pose are quadruped-only


def test_biped_walk_targets_limb_bones():
    spec = Spec.load(BIPED)
    skel = build_skeleton(spec, make_rng(spec.seed))
    walk = next(c for c in animate(skel, spec) if c.name == "walk")
    bones = {ch.bone for ch in walk.channels}
    assert {"thigh_l", "thigh_r", "upperarm_l", "upperarm_r"} <= bones

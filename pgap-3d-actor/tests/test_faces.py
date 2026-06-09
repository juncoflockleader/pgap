"""Roadmap 3 — V4 faces: the maw head's hinged jaw + pupilled eyes, and the
mouth_open / eye_look expression clips. We verify the rig actually deforms (the
jaw drops, the pupil swings) by applying the dominant-bone pose to the skinned
mesh — no engine needed."""

import numpy as np

from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.animate import animate_recipe
from pgap.v2.assembly import build_actor
from pgap.v2.library import maw_head_module
from pgap.v2.registry import MODULE_REGISTRY, load_template


def _spec(n="wolf", h=90):
    return Spec.from_dict({"name": n, "archetype": "biped", "species": n, "seed": 5,
                           "triBudget": 11000, "proportions": {"heightCm": h},
                           "material": {"baseColor": "tan", "eyeColor": "amber"}})


def _wolf():
    return build_actor(load_template("wolf"), _spec(), make_rng(5))


def _roty(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rotz(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def _dominant(mesh):
    return mesh.joints[np.arange(mesh.num_vertices), np.argmax(mesh.weights, axis=1)]


def test_maw_is_a_head_variant_with_a_jaw():
    assert "maw" in MODULE_REGISTRY["head"].variants
    assert {"skull", "snout", "jaw", "nose"} <= {b.name for b in maw_head_module().bones}


def test_wolf_builds_a_valid_face_rig():
    skel, mesh = _wolf()
    names = {b.name for b in skel}
    assert {"head_skull", "head_jaw", "head_nose",
            "eyes_eye_l", "eyes_pupil_l", "eyes_eye_r", "eyes_pupil_r"} <= names
    assert np.allclose(mesh.weights.sum(1), 1.0, atol=1e-5)        # rest pose skins cleanly


def test_expression_clips_target_the_face_bones():
    clips = {c.name: c for c in animate_recipe(load_template("wolf"), _spec())}
    assert {"idle", "mouth_open", "eye_look"} <= set(clips)
    assert any(ch.bone == "head_jaw" for ch in clips["mouth_open"].channels)
    assert {ch.bone for ch in clips["eye_look"].channels} == {"eyes_eye_l", "eyes_eye_r"}


def test_mouth_open_drops_the_jaw():
    skel, mesh = _wolf()
    bi = {b.name: i for i, b in enumerate(skel)}
    dom = _dominant(mesh)
    hinge = skel[bi["head_jaw"]].head.astype(float)
    jv = np.nonzero(dom == bi["head_jaw"])[0]
    P = mesh.positions.astype(float)
    posed = hinge + (P[jv] - hinge) @ _rotz(-24.0).T      # the mouth_open jaw pose
    assert (posed[:, 1] - P[jv, 1]).mean() < -0.005, "the jaw should swing down (maw opens)"
    # the upper skull is a separate bone and does not move
    assert not np.array_equal(jv, np.nonzero(dom == bi["head_skull"])[0])


def test_eye_look_swings_the_pupil():
    skel, mesh = _wolf()
    bi = {b.name: i for i, b in enumerate(skel)}
    dom = _dominant(mesh)
    pivot = skel[bi["eyes_eye_l"]].head.astype(float)
    pv = np.nonzero(dom == bi["eyes_pupil_l"])[0]
    assert len(pv) > 0
    P = mesh.positions.astype(float)
    posed = pivot + (P[pv] - pivot) @ _roty(18.0).T       # the eye_look gaze pose
    assert np.abs(posed[:, 2] - P[pv, 2]).mean() > 0.001, "the pupil should swing (gaze)"


def test_faces_deterministic():
    a = _wolf()[1]
    b = _wolf()[1]
    assert np.array_equal(a.positions, b.positions) and np.array_equal(a.colors, b.colors)

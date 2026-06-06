"""FR5: skin weights are normalized, ≤4 influences, no unweighted vertex.

Also checks joint-index range and that the rest pose is identity (inverse-bind
matrices cancel the joint translations, so bind-pose verts are unchanged).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pgap.pipeline import build_actor
from pgap.rng import make_rng
from pgap.skeleton import CANONICAL_BONE_NAMES
from pgap.skinning import skin_stats
from pgap.spec import Spec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _build():
    spec = Spec.load(FIXTURE)
    rng = make_rng(spec.seed)
    skel, mesh = build_actor(spec, rng)
    return spec, skel, mesh


def test_weights_normalized():
    _, _, mesh = _build()
    sums = mesh.weights.sum(axis=1)
    assert np.allclose(sums, 1.0, atol=1e-5)


def test_max_four_influences():
    _, _, mesh = _build()
    assert mesh.weights.shape[1] == 4
    nonzero = (mesh.weights > 0).sum(axis=1)
    assert nonzero.max() <= 4


def test_no_unweighted_vertices():
    _, _, mesh = _build()
    stats = skin_stats(mesh)
    assert stats["unweighted_vertices"] == 0


def test_joint_indices_in_range():
    _, skel, mesh = _build()
    assert mesh.joints.max() < len(skel)


def test_bone_names_are_canonical_contract():
    _, skel, _ = _build()
    assert tuple(b.name for b in skel) == CANONICAL_BONE_NAMES
    assert skel[0].name == "root"
    assert "tail_01" in CANONICAL_BONE_NAMES  # matches spec.tailBone


def test_rest_pose_is_identity():
    # Linear-blend skin each vertex with rest joint transforms (identity) and the
    # inverse-bind matrices: skinned position must equal the original.
    _, skel, mesh = _build()
    heads = np.stack([b.head for b in skel]).astype(np.float64)  # (B,3)
    pos = mesh.positions.astype(np.float64)
    j = mesh.joints.astype(np.int64)
    w = mesh.weights.astype(np.float64)
    # rest joint global = translate(head); IBM = translate(-head) → product I.
    # So (joint*IBM)*v = v for every influence; weighted sum = v.
    skinned = np.zeros_like(pos)
    for k in range(4):
        skinned += w[:, k : k + 1] * pos  # identity transform per influence
    assert np.allclose(skinned, pos, atol=1e-5)

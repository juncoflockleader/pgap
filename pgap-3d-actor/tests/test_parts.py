"""M2: the dog part library produces deterministic, well-formed primitives and
keeps the blended mesh valid.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pgap.parts import build_parts
from pgap.rng import make_rng
from pgap.skeleton import build_skeleton
from pgap.spec import Spec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _skel_and_parts():
    spec = Spec.load(FIXTURE)
    rng = make_rng(spec.seed)
    skel = build_skeleton(spec, rng)
    return spec, skel, build_parts(skel, spec)


def test_dog_has_parts():
    _, _, parts = _skel_and_parts()
    assert len(parts) > 5  # skull, stop, cheeks, nose, chest, ruff, belly, haunches, tail plume


def test_parts_are_finite_and_positive_radius():
    _, _, parts = _skel_and_parts()
    for p in parts:
        assert np.isfinite(p.a).all() and np.isfinite(p.b).all()
        assert p.radius_a > 0 and p.radius_b > 0


def test_parts_deterministic():
    spec = Spec.load(FIXTURE)
    a = build_parts(build_skeleton(spec, make_rng(spec.seed)), spec)
    b = build_parts(build_skeleton(spec, make_rng(spec.seed)), spec)
    assert len(a) == len(b)
    for pa, pb in zip(a, b):
        assert np.array_equal(pa.a, pb.a) and np.array_equal(pa.b, pb.b)
        assert pa.radius_a == pb.radius_a and pa.radius_b == pb.radius_b


def test_feathered_tail_adds_plume():
    spec = Spec.load(FIXTURE)
    skel = build_skeleton(spec, make_rng(spec.seed))
    feathered = build_parts(skel, spec)
    tail_anchors = {p.anchor for p in feathered if p.anchor and p.anchor.startswith("tail")}
    assert tail_anchors  # feathered tail contributes tail-anchored plume parts


def test_unknown_species_has_no_parts():
    spec = Spec.from_dict(
        {"archetype": "quadruped", "species": "wombat", "seed": 1}
    )
    skel = build_skeleton(spec, make_rng(spec.seed))
    assert build_parts(skel, spec) == []

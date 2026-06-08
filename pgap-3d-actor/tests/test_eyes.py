"""Eyes (organ part) + the foundational non-fused / region-tagged blob capability."""

import json
from pathlib import Path

import numpy as np

from pgap.geometry import build_geometry
from pgap.paint import paint_colors
from pgap.pipeline import build_actor
from pgap.rng import make_rng
from pgap.skeleton import build_skeleton
from pgap.skinning import skin
from pgap.spec import Spec
from pgap.types import Primitive

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _dog():
    spec = Spec.from_dict(json.loads((FIX / "dog_golden_retriever.json").read_text()))
    skel, mesh = build_actor(spec, make_rng(spec.seed))
    return skel, mesh


def test_dog_has_two_dark_eyes():
    _, mesh = _dog()
    lum = mesh.colors[:, :3].mean(axis=1)
    dark = lum < 0.25
    pos = mesh.positions[dark]
    assert dark.sum() >= 20, f"too few eye verts: {int(dark.sum())}"
    # symmetric: eyes on both sides of the midline
    assert (pos[:, 2] > 0).sum() >= 5 and (pos[:, 2] < 0).sum() >= 5
    # up on the head (front, above the body), not on the torso
    assert pos[:, 1].min() > 0.5


def test_dog_has_black_nose_and_mouth():
    _, mesh = _dog()
    lum = mesh.colors[:, :3].mean(axis=1)
    very_dark = lum < 0.25
    pos = mesh.positions[very_dark]
    # the nose is the front-most dark cluster (largest x, near the midline)
    front_x = pos[:, 0].max()
    nose = pos[(pos[:, 0] > front_x - 0.06)]
    assert len(nose) >= 3, "no black nose at the snout tip"
    assert np.abs(nose[:, 2]).mean() < 0.06, "nose should sit near the midline"
    # total facial dark (eyes + nose + mouth) is clearly more than eyes alone
    assert very_dark.sum() >= 40


def test_primitive_defaults_unchanged():
    p = Primitive(a=np.zeros(3, np.float32), b=np.zeros(3, np.float32),
                  radius_a=0.1, radius_b=0.1)
    assert p.fused is True and p.region is None


def _proud_sphere(head, scale=0.8, fused=False, region=None):
    """A sphere sitting proud of the head surface (poking out the top)."""
    up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    center = head.tail.astype(np.float32) + up * float(head.radius_head)
    r = float(head.radius_head * scale)
    return Primitive(a=center, b=center, radius_a=r, radius_b=r, fused=fused, region=region)


def test_non_fused_blob_stays_distinct():
    # A non-fused sphere poking out of the body should add surface (a bump),
    # not melt fully into the smooth-min body.
    spec = Spec.from_dict(json.loads((FIX / "dog_golden_retriever.json").read_text()))
    skel = build_skeleton(spec, make_rng(spec.seed))
    head = next(b for b in skel if b.name == "head")
    bump = _proud_sphere(head)
    m_plain = build_geometry(skel, spec, make_rng(spec.seed))
    m_bump = build_geometry(skel, spec, make_rng(spec.seed), (bump,))
    assert m_bump.num_vertices > m_plain.num_vertices


def test_region_tag_overrides_bone_color():
    spec = Spec.from_dict(json.loads((FIX / "dog_golden_retriever.json").read_text()))
    skel = build_skeleton(spec, make_rng(spec.seed))
    head = next(b for b in skel if b.name == "head")
    eye = _proud_sphere(head, scale=0.6, region="eyes")
    mesh = build_geometry(skel, spec, make_rng(spec.seed), (eye,))
    mesh = skin(mesh, skel)
    painted = paint_colors(mesh, skel, spec, (eye,))
    # some verts near the eye are colored dark (the eyes region)
    assert (painted.colors[:, :3].mean(axis=1) < 0.25).sum() > 0


def test_eyes_deterministic():
    _, a = _dog()
    _, b = _dog()
    assert np.array_equal(a.positions, b.positions)
    assert np.array_equal(a.colors, b.colors)

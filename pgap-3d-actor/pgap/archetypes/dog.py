"""Dog part library (M2) — extra SDF detail that makes the quadruped read as a
golden retriever.

Parts are positioned **relative to named bones** and sized **relative to bone
radii**, so they track proportions + global scale automatically and bind by
proximity to the nearest bone during skinning (no skinning changes needed). Ear
shape is handled by the rig (see ``skeleton.py``); this module adds the skull
dome + stop, cheeks, nose, deep chest/brisket, neck ruff, hindquarters, and an
underside tail plume for the feathered tail.

All analytic and deterministic (no RNG).
"""

from __future__ import annotations

import numpy as np

from ..spec import Spec
from ..types import Bone, Primitive

_F = np.float32
_UP = np.array([0.0, 1.0, 0.0])
_FWD = np.array([1.0, 0.0, 0.0])


def _sphere(center: np.ndarray, radius: float, anchor: str,
            fused: bool = True, region: str | None = None) -> Primitive:
    c = center.astype(_F)
    return Primitive(a=c, b=c, radius_a=float(radius), radius_b=float(radius),
                     anchor=anchor, fused=fused, region=region)


def _norm(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else v


def _capsule(a: np.ndarray, b: np.ndarray, ra: float, rb: float, anchor: str) -> Primitive:
    return Primitive(a=a.astype(_F), b=b.astype(_F), radius_a=float(ra), radius_b=float(rb), anchor=anchor)


def _along(bone: Bone, t: float) -> np.ndarray:
    h = bone.head.astype(np.float64)
    return h + t * (bone.tail.astype(np.float64) - h)


def build(skel: list[Bone], spec: Spec) -> list[Primitive]:
    B = {b.name: b for b in skel}
    head, neck, snout = B["head"], B["neck_01"], B["snout"]
    spine1, spine2, root = B["spine_01"], B["spine_02"], B["root"]
    rh = head.radius_head  # head radius drives facial feature scale
    parts: list[Primitive] = []

    # --- head: rounder skull + forehead stop, cheeks, rounded nose -----------
    parts.append(_sphere(_along(head, 0.30) + _UP * 0.45 * rh, rh * 1.00, "head"))
    parts.append(_sphere(head.tail.astype(np.float64) + _UP * 0.25 * rh, rh * 0.62, "head"))  # stop/brow
    for sign in (1.0, -1.0):
        cheek = _along(snout, 0.18) + np.array([0.0, -0.1 * rh, sign * 0.55 * snout.radius_head])
        parts.append(_sphere(cheek, snout.radius_head * 0.85, "head"))
    parts.append(_sphere(snout.tail.astype(np.float64), snout.radius_tail * 1.15, "snout"))  # nose

    # --- eyes: two dark, non-fused "bead" eyes on the front-upper sides of the skull
    fwd = _norm(head.tail.astype(np.float64) - head.head.astype(np.float64))
    front = _along(head, 0.86)
    for sign in (1.0, -1.0):
        out = _norm(fwd * 0.5 + _UP * 0.42 + np.array([0.0, 0.0, sign]) * 0.9)
        eye_c = front + out * (rh * 0.86)
        parts.append(_sphere(eye_c, rh * 0.46, "head", fused=False, region="eyes"))

    # --- deep chest / brisket and neck ruff ----------------------------------
    chest_a = spine2.head.astype(np.float64) + _UP * (-0.45 * spine2.radius_head) + _FWD * 0.02
    chest_b = _along(neck, 0.25) + _UP * (-0.75 * neck.radius_head)
    parts.append(_capsule(chest_a, chest_b, spine2.radius_head * 1.02, neck.radius_head * 0.85, "spine_02"))
    ruff_a = neck.head.astype(np.float64) + _UP * (-0.15 * neck.radius_head)
    ruff_b = _along(neck, 0.7)
    parts.append(_capsule(ruff_a, ruff_b, neck.radius_head * 0.95, neck.radius_tail * 0.85, "neck_01"))

    # --- belly fullness (gentle underline) -----------------------------------
    parts.append(
        _capsule(
            _along(spine1, 0.2) + _UP * (-0.35 * spine1.radius_head),
            _along(root, 0.6) + _UP * (-0.35 * root.radius_head),
            spine1.radius_head * 0.92, root.radius_head * 0.92, "spine_01",
        )
    )

    # --- full hindquarters (golden retriever has muscular rear) ---------------
    for tag in ("thigh_hl", "thigh_hr"):
        thigh = B[tag]
        parts.append(_sphere(_along(thigh, 0.25), thigh.radius_head * 1.15, tag))

    # --- feathered tail: underside plume -------------------------------------
    if str(spec.traits.get("tail", "feathered")) == "feathered":
        for tag in ("tail_01", "tail_02", "tail_03"):
            tb = B[tag]
            a = tb.head.astype(np.float64) + _UP * (-0.5 * tb.radius_head)
            b = tb.tail.astype(np.float64) + _UP * (-0.4 * tb.radius_tail)
            parts.append(_capsule(a, b, tb.radius_head * 1.7, tb.radius_tail * 1.7, tag))

    return parts

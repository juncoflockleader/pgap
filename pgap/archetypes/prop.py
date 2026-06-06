"""Static-prop part library (M6).

Props have no skeleton: the geometry is just a blended cluster of SDF primitives.
``build(spec, rng) -> list[Primitive]`` returns those blobs; the geometry kernel
meshes them exactly as it meshes bone capsules. Default is a seed-jittered rock;
``barrel`` is a variant. Deterministic (rock uses the threaded seeded RNG).
"""

from __future__ import annotations

import numpy as np

from ..rng import Rng
from ..spec import Spec
from ..types import Primitive

_F = np.float32


def _sphere(center, radius, anchor="prop") -> Primitive:
    c = np.asarray(center, dtype=_F)
    return Primitive(a=c, b=c, radius_a=float(radius), radius_b=float(radius), anchor=anchor)


def _capsule(a, b, ra, rb, anchor="prop") -> Primitive:
    return Primitive(a=np.asarray(a, dtype=_F), b=np.asarray(b, dtype=_F),
                     radius_a=float(ra), radius_b=float(rb), anchor=anchor)


def _scale(spec: Spec) -> float:
    return float(spec.proportions["heightCm"]) / 60.0


def _rock(spec: Spec, rng: Rng) -> list[Primitive]:
    s = _scale(spec)
    parts = [_sphere((0.0, 0.16 * s, 0.0), 0.15 * s)]  # core, sitting near ground
    extent = np.array([0.17, 0.11, 0.15]) * s
    for _ in range(6):
        center = (rng.random(3) * 2.0 - 1.0) * extent
        center[1] = abs(center[1]) + 0.12 * s  # keep above ground
        radius = (0.08 + 0.06 * rng.random()) * s
        parts.append(_sphere(center, radius))
    return parts


def _barrel(spec: Spec) -> list[Primitive]:
    s = _scale(spec)
    return [
        _capsule((0.0, 0.04 * s, 0.0), (0.0, 0.46 * s, 0.0), 0.15 * s, 0.15 * s),  # body
        _sphere((0.0, 0.25 * s, 0.0), 0.185 * s),  # mid bulge
    ]


def build(spec: Spec, rng: Rng) -> list[Primitive]:
    kind = str(spec.species).lower()
    if "barrel" in kind or "cask" in kind:
        return _barrel(spec)
    return _rock(spec, rng)

"""Core data structures shared across stages (DESIGN §2).

Kept minimal for M0: a ``Bone`` segment with a tapered radius, a ``Skeleton`` as
an ordered list of bones, and a ``Mesh`` carrying geometry. Skin/UV fields exist
on ``Mesh`` but stay ``None`` until M1/M4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class Primitive:
    """An extra (non-bone) SDF blob for the part library (M2).

    A tapered capsule from ``a`` to ``b``; a sphere is ``a == b``. ``anchor`` is
    documentation only (the bone the part conceptually belongs to) — skinning
    binds parts by proximity, not by this field.

    ``fused=False`` makes the blob a *non-fused organ*: it is hard-min'd (plain
    union, a crease) with the body instead of smooth-min'd, so a small sphere like
    an eyeball sits *proud* as a distinct bead rather than melting into the surface.
    It must still overlap the body to survive the largest-component cleanup.

    ``region`` tags the blob's surface so paint can color it independently of the
    nearest bone (e.g. a dark ``"eyes"`` iris on a head-colored skull).
    """

    a: np.ndarray  # f32[3]
    b: np.ndarray  # f32[3]
    radius_a: float
    radius_b: float
    anchor: Optional[str] = None
    fused: bool = True
    region: Optional[str] = None


@dataclass(frozen=True)
class Bone:
    """A canonical rig node: a rest-pose segment with a tapered radius.

    ``head``/``tail`` are the segment endpoints (world rest pose). The radii
    drive the tapered-capsule SDF the geometry kernel sweeps along the segment.
    """

    name: str
    parent: Optional[str]
    head: np.ndarray  # f32[3]
    tail: np.ndarray  # f32[3]
    radius_head: float
    radius_tail: float


# Topologically sorted, root first.
Skeleton = list


@dataclass(frozen=True)
class Mesh:
    """Triangle mesh. M0 fills positions/normals/indices only."""

    positions: np.ndarray  # f32[N,3]
    normals: np.ndarray  # f32[N,3]
    indices: np.ndarray  # u32[M] (flat, 3 per triangle)
    uvs: Optional[np.ndarray] = None  # f32[N,2]
    joints: Optional[np.ndarray] = None  # u16[N,4]
    weights: Optional[np.ndarray] = None  # f32[N,4]
    colors: Optional[np.ndarray] = None  # f32[N,4] vertex color (COLOR_0)

    @property
    def num_vertices(self) -> int:
        return int(self.positions.shape[0])

    @property
    def num_triangles(self) -> int:
        return int(self.indices.shape[0] // 3)


@dataclass(frozen=True)
class Channel:
    """One animated track targeting a joint (DESIGN §2).

    ``path`` is ``"rotation"`` (values f32[T,4] xyzw quaternion) or
    ``"translation"`` (values f32[T,3]). Sampled at the owning clip's times.
    """

    bone: str
    path: str
    values: np.ndarray


@dataclass(frozen=True)
class AnimClip:
    """A canonical animation clip: one shared time track + per-joint channels."""

    name: str
    times: np.ndarray  # f32[T], seconds; loop-seamless (values[-1] == values[0])
    channels: list  # list[Channel]

    @property
    def duration(self) -> float:
        return float(self.times[-1]) if self.times.size else 0.0

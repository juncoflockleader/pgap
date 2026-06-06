"""UV layout (DESIGN §3 UV, M4).

A cylindrical unwrap about the body's long axis (+X): ``u`` from the angle in the
Y/Z plane, ``v`` from the normalized along-body position. Valid ``[0,1]`` with
consistent texel density; seams are acceptable for the stylized fur (DESIGN:
determinism over perfection). This carries the tiling fur texture; per-region
color comes from vertex tint (see ``paint.py``).
"""

from __future__ import annotations

import numpy as np

from .spec import Spec
from .types import Bone, Mesh

_F = np.float32


def layout_uvs(mesh: Mesh, skel: list[Bone], spec: Spec) -> Mesh:
    pos = mesh.positions.astype(np.float64)
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    u = np.arctan2(z, y) / (2.0 * np.pi) + 0.5
    x_min, x_max = float(x.min()), float(x.max())
    v = (x - x_min) / (x_max - x_min + 1e-9)
    uvs = np.stack([u, v], axis=1).astype(_F)
    return Mesh(
        positions=mesh.positions,
        normals=mesh.normals,
        indices=mesh.indices,
        uvs=uvs,
        joints=mesh.joints,
        weights=mesh.weights,
        colors=mesh.colors,
    )

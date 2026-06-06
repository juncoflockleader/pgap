"""Per-vertex region tint (M4).

Sets ``COLOR_0`` so that, when glTF multiplies it by the golden-fur base texture,
each region renders close to its target coat color: golden back, darker ears,
cream belly/chest, lighter muzzle, cream lower-leg/tail feathering. Region is
chosen from the vertex's dominant bone (plus a belly test on body vertices).

`color = clamp(target / base_coat)` so `base_texture (~base_coat) × color ≈ target`.
Deterministic (no RNG).
"""

from __future__ import annotations

import numpy as np

from . import palette
from .spec import Spec
from .types import Bone, Mesh

_F = np.float32

# dominant bone name -> region key (belly is decided per-vertex on body bones).
_BONE_REGION = {
    "ear_l": "ears", "ear_r": "ears",
    "snout": "muzzle",
    "head": "head", "neck_01": "head",
    "tail_01": "tail", "tail_02": "tail", "tail_03": "tail",
}


def _region_for(bone_name: str) -> str:
    if bone_name in _BONE_REGION:
        return _BONE_REGION[bone_name]
    if bone_name.startswith(("shin_", "paw_")):
        return "legs"
    if bone_name.startswith("thigh_"):
        return "body"
    return "body"  # root, spine_*


def paint_colors(mesh: Mesh, skel: list[Bone], spec: Spec) -> Mesh:
    assert mesh.joints is not None and mesh.weights is not None, "skin before painting"
    names = [b.name for b in skel]
    dominant = mesh.joints[np.arange(mesh.num_vertices), np.argmax(mesh.weights, axis=1)]

    spine_ys = [b.head[1] for b in skel if b.name.startswith(("root", "spine"))]
    body_mid = float(np.mean(spine_ys)) if spine_ys else 0.0

    base = palette.base_coat(spec.material).astype(np.float64)
    colors = np.ones((mesh.num_vertices, 4), dtype=_F)
    for i in range(mesh.num_vertices):
        region = _region_for(names[int(dominant[i])])
        if region == "body" and mesh.positions[i, 1] < body_mid:
            region = "belly"
        target = palette.region_color(spec.material, region).astype(np.float64)
        rgb = np.clip(target / np.maximum(base, 1e-3), 0.0, 4.0)
        colors[i, :3] = rgb.astype(_F)
    return Mesh(
        positions=mesh.positions,
        normals=mesh.normals,
        indices=mesh.indices,
        uvs=mesh.uvs,
        joints=mesh.joints,
        weights=mesh.weights,
        colors=colors,
    )

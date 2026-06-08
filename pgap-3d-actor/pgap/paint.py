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


def _seg_distance(positions: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance from each vertex (V,3) to the segment a..b (V,)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ba = b - a
    denom = float(ba @ ba)
    pa = positions.astype(np.float64) - a
    if denom <= 1e-12:
        h = np.zeros(positions.shape[0], dtype=np.float64)
    else:
        h = np.clip((pa @ ba) / denom, 0.0, 1.0)
    closest = a + h[:, None] * ba
    return np.linalg.norm(positions.astype(np.float64) - closest, axis=1)


def paint_colors(mesh: Mesh, skel: list[Bone], spec: Spec, parts: tuple = ()) -> Mesh:
    assert mesh.joints is not None and mesh.weights is not None, "skin before painting"
    dominant = mesh.joints[np.arange(mesh.num_vertices), np.argmax(mesh.weights, axis=1)]

    spine_ys = [b.head[1] for b in skel if b.name.startswith(("root", "spine"))]
    body_mid = float(np.mean(spine_ys)) if spine_ys else 0.0

    # Region per vertex from the dominant bone (+ belly test on body vertices).
    # A bone may name its own region (v2 organs, e.g. an eyeball's dark "eyes");
    # that wins over the name-based lookup so the organ colors independently.
    regions = []
    for i in range(mesh.num_vertices):
        bone = skel[int(dominant[i])]
        region = getattr(bone, "region", None) or _region_for(bone.name)
        if region == "body" and mesh.positions[i, 1] < body_mid:
            region = "belly"
        regions.append(region)

    # Region-tagged parts (e.g. eyes) override the bone region by proximity, so an
    # organ can be colored independently of the bone it's skinned to.
    for p in parts:
        region = getattr(p, "region", None)
        if not region:
            continue
        reach = max(float(p.radius_a), float(p.radius_b)) * 1.3
        near = _seg_distance(mesh.positions, p.a, p.b) <= reach
        for i in np.nonzero(near)[0]:
            regions[int(i)] = region

    base = palette.base_coat(spec.material).astype(np.float64)
    colors = np.ones((mesh.num_vertices, 4), dtype=_F)
    for i in range(mesh.num_vertices):
        if regions[i] == "eyes":  # iris hue (material.eyeColor), else default dark
            target = palette.eye_color(spec.material).astype(np.float64)
        else:
            target = palette.region_color(spec.material, regions[i]).astype(np.float64)
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

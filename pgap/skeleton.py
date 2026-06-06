"""Canonical quadruped rig + proportioning (DESIGN §3 skeleton builder, M1).

The rig is **data**: a frozen bone graph with rest positions and a scaling group
per bone. Bone names are the contract with the M3 animation library and the
``import.json`` sidecar — do not rename them casually.

Build = take the canonical rest pose, derive each bone's attach point (projection
of its head onto the parent segment) + lateral offset, then rebuild world
positions in topological order applying per-group length factors from
``spec.proportions``/``traits``. Scaling a parent therefore moves its whole
subtree. A uniform ``heightCm`` scale and a ground-clamp finish. Fully analytic
and deterministic — no RNG draws in M1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .rng import Rng
from .spec import Spec
from .types import Bone

_F = np.float32
REF_HEIGHT_CM = 60.0  # canonical rest pose is authored at ~0.6 m tall


def _v(x: float, y: float, z: float) -> np.ndarray:
    return np.array([x, y, z], dtype=np.float64)


@dataclass(frozen=True)
class _Tmpl:
    name: str
    parent: str | None
    head: np.ndarray
    tail: np.ndarray
    radius_head: float
    radius_tail: float
    group: str  # spine | neck | head | snout | ear | tail | leg | none


# Canonical rest pose. glTF Y-up, +X forward (nose), +Z = animal's left.
# Authored by hand for a neutral quadruped at ~0.6 m tall (all proportions 1.0).
def _front_leg(side: str, z: float) -> list[_Tmpl]:
    return [
        _Tmpl(f"thigh_f{side}", "spine_02", _v(0.22, 0.44, z), _v(0.24, 0.24, z + 0.01), 0.07, 0.05, "leg"),
        _Tmpl(f"shin_f{side}", f"thigh_f{side}", _v(0.24, 0.24, z + 0.01), _v(0.25, 0.07, z + 0.02), 0.05, 0.035, "leg"),
        _Tmpl(f"paw_f{side}", f"shin_f{side}", _v(0.25, 0.07, z + 0.02), _v(0.30, 0.0, z + 0.02), 0.045, 0.04, "leg"),
    ]


def _hind_leg(side: str, z: float) -> list[_Tmpl]:
    return [
        _Tmpl(f"thigh_h{side}", "root", _v(-0.28, 0.44, z), _v(-0.30, 0.24, z + 0.01), 0.08, 0.055, "leg"),
        _Tmpl(f"shin_h{side}", f"thigh_h{side}", _v(-0.30, 0.24, z + 0.01), _v(-0.29, 0.07, z + 0.02), 0.055, 0.035, "leg"),
        _Tmpl(f"paw_h{side}", f"shin_h{side}", _v(-0.29, 0.07, z + 0.02), _v(-0.24, 0.0, z + 0.02), 0.045, 0.04, "leg"),
    ]


_RIG: list[_Tmpl] = [
    # axial chain (root first, topologically sorted)
    _Tmpl("root", None, _v(-0.35, 0.46, 0.0), _v(-0.10, 0.47, 0.0), 0.15, 0.15, "spine"),
    _Tmpl("spine_01", "root", _v(-0.10, 0.47, 0.0), _v(0.20, 0.46, 0.0), 0.15, 0.14, "spine"),
    _Tmpl("spine_02", "spine_01", _v(0.20, 0.46, 0.0), _v(0.40, 0.50, 0.0), 0.14, 0.11, "spine"),
    _Tmpl("neck_01", "spine_02", _v(0.40, 0.50, 0.0), _v(0.52, 0.62, 0.0), 0.10, 0.09, "neck"),
    _Tmpl("head", "neck_01", _v(0.52, 0.62, 0.0), _v(0.60, 0.64, 0.0), 0.11, 0.10, "head"),
    _Tmpl("snout", "head", _v(0.60, 0.64, 0.0), _v(0.74, 0.59, 0.0), 0.06, 0.035, "snout"),
    _Tmpl("ear_l", "head", _v(0.54, 0.66, 0.09), _v(0.50, 0.60, 0.11), 0.035, 0.02, "ear"),
    _Tmpl("ear_r", "head", _v(0.54, 0.66, -0.09), _v(0.50, 0.60, -0.11), 0.035, 0.02, "ear"),
    _Tmpl("tail_01", "root", _v(-0.35, 0.47, 0.0), _v(-0.48, 0.50, 0.0), 0.05, 0.04, "tail"),
    _Tmpl("tail_02", "tail_01", _v(-0.48, 0.50, 0.0), _v(-0.58, 0.54, 0.0), 0.04, 0.03, "tail"),
    _Tmpl("tail_03", "tail_02", _v(-0.58, 0.54, 0.0), _v(-0.68, 0.57, 0.0), 0.03, 0.02, "tail"),
]
_RIG += _front_leg("l", 0.12) + _front_leg("r", -0.12)
_RIG += _hind_leg("l", 0.12) + _hind_leg("r", -0.12)

CANONICAL_BONE_NAMES: tuple[str, ...] = tuple(t.name for t in _RIG)


# Ear styles: canonical-space tail offset from the ear head + flap radii.
# floppy = fat flap drooping beside the cheek (golden retriever); pointy = upright.
_EAR_STYLES = {
    "floppy": {"offset": np.array([0.01, -0.22, 0.07]), "rh": 0.06, "rt": 0.038},
    "pointy": {"offset": np.array([-0.02, 0.13, 0.02]), "rh": 0.03, "rt": 0.012},
}


def _ear_style(spec: Spec) -> dict:
    return _EAR_STYLES.get(str(spec.traits.get("ears", "floppy")), _EAR_STYLES["floppy"])


def _group_factors(spec: Spec) -> dict[str, float]:
    prop = spec.proportions
    snout_map = {"short": 0.7, "medium": 1.0, "long": 1.3}
    return {
        "spine": float(prop["bodyLength"]),
        "neck": float(prop["neck"]),
        "tail": float(prop["tail"]),
        "leg": float(prop["legLength"]),
        "snout": snout_map.get(str(spec.traits.get("snout", "medium")), 1.0),
        "head": 1.0,
        "ear": 1.0,
        "none": 1.0,
    }


def build_skeleton(spec: Spec, rng: Rng) -> list[Bone]:
    """Canonical rig proportioned per the spec. ``rng`` unused (analytic in M1)."""
    factors = _group_factors(spec)
    ear = _ear_style(spec)
    canon = {t.name: (t.head, t.tail) for t in _RIG}
    built: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for t in _RIG:
        vec = (t.tail - t.head) * factors.get(t.group, 1.0)
        if t.parent is None:
            head = t.head.copy()
        else:
            p_head_c, p_tail_c = canon[t.parent]
            seg = p_tail_c - p_head_c
            denom = float(seg @ seg)
            attach = 0.0 if denom < 1e-12 else float(np.clip(((t.head - p_head_c) @ seg) / denom, 0.0, 1.0))
            lateral = t.head - (p_head_c + attach * seg)
            bp_head, bp_tail = built[t.parent]
            head = bp_head + attach * (bp_tail - bp_head) + lateral
        if t.group == "ear":
            # Override the ear direction by style; sign the lateral axis per side.
            side = 1.0 if t.head[2] >= 0.0 else -1.0
            off = ear["offset"].copy()
            off[2] *= side
            built[t.name] = (head, head + off)
        else:
            built[t.name] = (head, head + vec)

    global_scale = float(spec.proportions["heightCm"]) / REF_HEIGHT_CM

    # Ground-clamp: shift so the lowest point (paw bottom) rests at y = 0.
    min_y = min(
        min(built[t.name][0][1] - t.radius_head, built[t.name][1][1] - t.radius_tail)
        for t in _RIG
    ) * global_scale

    bones: list[Bone] = []
    for t in _RIG:
        head, tail = built[t.name]
        head = head * global_scale
        tail = tail * global_scale
        head[1] -= min_y
        tail[1] -= min_y
        if t.group == "ear":
            r_head, r_tail = ear["rh"], ear["rt"]
        else:
            r_head, r_tail = t.radius_head, t.radius_tail
        bones.append(
            Bone(
                name=t.name,
                parent=t.parent,
                head=head.astype(_F),
                tail=tail.astype(_F),
                radius_head=float(r_head * global_scale),
                radius_tail=float(r_tail * global_scale),
            )
        )
    return bones

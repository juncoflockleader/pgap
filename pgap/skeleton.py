"""Canonical rigs + proportioning (DESIGN §3 skeleton builder, M1 + M6).

Rigs are **data**: a frozen bone graph with rest positions and a scaling group per
bone. Bone names are the contract with the animation library and the import
sidecar. ``build_skeleton`` dispatches by archetype (quadruped | biped); props
have no skeleton.

Build = take the canonical rest pose, derive each bone's attach point (projection
of its head onto the parent segment) + lateral offset, then rebuild world
positions in topological order applying per-group length factors. Scaling a parent
moves its whole subtree. A uniform ``heightCm`` scale + ground-clamp finish.
Analytic and deterministic — no RNG draws.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .rng import Rng
from .spec import Spec
from .types import Bone

_F = np.float32
REF_HEIGHT_CM = 60.0  # canonical rest poses are authored at ~0.6 m tall


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
    group: str  # spine | neck | head | snout | ear | tail | leg | arm | none


# --------------------------------------------------------------------------- #
# Quadruped rig (M1) — glTF Y-up, +X forward (nose), +Z = animal's left.
# --------------------------------------------------------------------------- #
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


_QUAD_RIG: list[_Tmpl] = [
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
_QUAD_RIG += _front_leg("l", 0.12) + _front_leg("r", -0.12)
_QUAD_RIG += _hind_leg("l", 0.12) + _hind_leg("r", -0.12)


# --------------------------------------------------------------------------- #
# Biped rig (M6) — upright, ~0.6 m canonical; +X forward, +Y up, +Z = left.
# --------------------------------------------------------------------------- #
def _arm(side: str, z: float) -> list[_Tmpl]:
    return [
        _Tmpl(f"upperarm_{side}", "spine_02", _v(0.0, 0.53, z), _v(0.0, 0.42, z + 0.05), 0.032, 0.026, "arm"),
        _Tmpl(f"forearm_{side}", f"upperarm_{side}", _v(0.0, 0.42, z + 0.05), _v(0.0, 0.30, z + 0.07), 0.026, 0.020, "arm"),
        _Tmpl(f"hand_{side}", f"forearm_{side}", _v(0.0, 0.30, z + 0.07), _v(0.0, 0.25, z + 0.075), 0.022, 0.018, "arm"),
    ]


def _leg(side: str, z: float) -> list[_Tmpl]:
    return [
        _Tmpl(f"thigh_{side}", "root", _v(0.0, 0.32, z), _v(0.0, 0.17, z + 0.005), 0.038, 0.030, "leg"),
        _Tmpl(f"shin_{side}", f"thigh_{side}", _v(0.0, 0.17, z + 0.005), _v(0.0, 0.04, z + 0.01), 0.030, 0.022, "leg"),
        _Tmpl(f"foot_{side}", f"shin_{side}", _v(0.0, 0.04, z + 0.01), _v(0.07, 0.0, z + 0.01), 0.028, 0.022, "leg"),
    ]


_BIPED_RIG: list[_Tmpl] = [
    _Tmpl("root", None, _v(0.0, 0.32, 0.0), _v(0.0, 0.40, 0.0), 0.075, 0.070, "spine"),
    _Tmpl("spine_01", "root", _v(0.0, 0.40, 0.0), _v(0.0, 0.48, 0.0), 0.070, 0.062, "spine"),
    _Tmpl("spine_02", "spine_01", _v(0.0, 0.48, 0.0), _v(0.0, 0.54, 0.0), 0.066, 0.050, "spine"),
    _Tmpl("neck_01", "spine_02", _v(0.0, 0.54, 0.0), _v(0.0, 0.575, 0.0), 0.026, 0.024, "neck"),
    _Tmpl("head", "neck_01", _v(0.0, 0.575, 0.0), _v(0.0, 0.63, 0.0), 0.052, 0.050, "head"),
]
_BIPED_RIG += _arm("l", 0.075) + _arm("r", -0.075)
_BIPED_RIG += _leg("l", 0.045) + _leg("r", -0.045)


CANONICAL_BONE_NAMES: tuple[str, ...] = tuple(t.name for t in _QUAD_RIG)
BIPED_BONE_NAMES: tuple[str, ...] = tuple(t.name for t in _BIPED_RIG)

_RIGS = {"quadruped": _QUAD_RIG, "biped": _BIPED_RIG}

# Ear styles (quadruped): canonical-space tail offset from the ear head + radii.
_EAR_STYLES = {
    "floppy": {"offset": np.array([0.01, -0.22, 0.07]), "rh": 0.06, "rt": 0.038},
    "pointy": {"offset": np.array([-0.02, 0.13, 0.02]), "rh": 0.03, "rt": 0.012},
}


def _group_factors(spec: Spec) -> dict[str, float]:
    prop = spec.proportions
    snout_map = {"short": 0.7, "medium": 1.0, "long": 1.3}
    return {
        "spine": float(prop["bodyLength"]),
        "neck": float(prop["neck"]),
        "tail": float(prop["tail"]),
        "leg": float(prop["legLength"]),
        "arm": float(prop.get("arm", prop["legLength"])),
        "snout": snout_map.get(str(spec.traits.get("snout", "medium")), 1.0),
        "head": 1.0, "ear": 1.0, "none": 1.0,
    }


def _assemble_bones(templates: list[_Tmpl], spec: Spec, ear: dict | None) -> list[Bone]:
    factors = _group_factors(spec)
    canon = {t.name: (t.head, t.tail) for t in templates}
    built: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for t in templates:
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
        if t.group == "ear" and ear is not None:
            side = 1.0 if t.head[2] >= 0.0 else -1.0
            off = ear["offset"].copy()
            off[2] *= side
            built[t.name] = (head, head + off)
        else:
            built[t.name] = (head, head + vec)

    global_scale = float(spec.proportions["heightCm"]) / REF_HEIGHT_CM
    min_y = min(
        min(built[t.name][0][1] - t.radius_head, built[t.name][1][1] - t.radius_tail)
        for t in templates
    ) * global_scale

    bones: list[Bone] = []
    for t in templates:
        head, tail = built[t.name]
        head = head * global_scale
        tail = tail * global_scale
        head[1] -= min_y
        tail[1] -= min_y
        if t.group == "ear" and ear is not None:
            r_head, r_tail = ear["rh"], ear["rt"]
        else:
            r_head, r_tail = t.radius_head, t.radius_tail
        bones.append(
            Bone(
                name=t.name, parent=t.parent,
                head=head.astype(_F), tail=tail.astype(_F),
                radius_head=float(r_head * global_scale),
                radius_tail=float(r_tail * global_scale),
            )
        )
    return bones


def build_skeleton(spec: Spec, rng: Rng) -> list[Bone]:
    """Canonical rig for the spec's archetype. Props have no skeleton ([])."""
    if spec.archetype == "prop":
        return []
    templates = _RIGS.get(spec.archetype)
    if templates is None:
        raise ValueError(f"no rig for archetype {spec.archetype!r}")
    ear = _EAR_STYLES.get(str(spec.traits.get("ears", "floppy"))) if spec.archetype == "quadruped" else None
    return _assemble_bones(templates, spec, ear)

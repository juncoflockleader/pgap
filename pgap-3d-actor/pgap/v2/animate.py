"""Modular animation (V2-M3 + V4 faces).

Each module *kind* contributes motion for its own bones; a named clip is the sum
of every instance's contribution. Animators are **clip-aware**: body modules move
in ``idle`` (tail-wag, wing-flap, sway), while the face rig drives ``mouth_open``
(a maw head's ``jaw`` bone rotates open/closed — bark/roar) and ``eye_look`` (the
``eyes`` sclera bones rotate so the pupils riding them gaze side to side). Tracks
are joint rotations (applied about each joint's head). Frequencies are integer
cycle-counts over the clip duration so clips loop seamlessly; ring instances are
de-phased by index so radial copies move out of unison.

Deterministic, analytic. Frame: +X fwd, +Y up, +Z left.
"""

from __future__ import annotations

import numpy as np

from ..types import AnimClip, Channel
from .assembly import assemble_with_meta

_F = np.float32
_X = np.array([1.0, 0.0, 0.0])
_Y = np.array([0.0, 1.0, 0.0])
_Z = np.array([0.0, 0.0, 1.0])

_DURATION = 3.0  # seconds; cycle counts below are integers over this window
_SAMPLES = 37


def _times() -> np.ndarray:
    return np.linspace(0.0, _DURATION, _SAMPLES)


def _quat(axis: np.ndarray, angle: np.ndarray) -> np.ndarray:
    ax = axis / (np.linalg.norm(axis) + 1e-12)
    h = angle * 0.5
    s = np.sin(h)
    out = np.empty((angle.shape[0], 4), dtype=np.float64)
    out[:, 0], out[:, 1], out[:, 2], out[:, 3] = ax[0] * s, ax[1] * s, ax[2] * s, np.cos(h)
    return out


def _rot(bone: str, axis: np.ndarray, angle: np.ndarray) -> Channel:
    return Channel(bone=bone, path="rotation", values=_quat(axis, angle).astype(_F))


def _w(cycles: float) -> float:
    return 2.0 * np.pi * cycles / _DURATION


# --- per-module animators: (inst, t, clip) -> list[Channel] ---------------- #
def _chain_anim(inst, t, clip):
    """Tentacle / tail: a travelling wave down the segments, rising to the tip."""
    if clip != "idle":
        return []
    names = inst["local_bones"]
    n = max(1, len(names) - 1)
    w = _w(2)
    phase = inst["phase"] * 0.7
    chans = []
    for k, ln in enumerate(names):
        amp = np.deg2rad(7.0 + 16.0 * (k / n))
        chans.append(_rot(f"{inst['id']}_{ln}", _Z, amp * np.sin(w * t - 0.8 * k - phase)))
    return chans


def _eyestalk_anim(inst, t, clip):
    if clip != "idle":
        return []
    w = _w(1)
    phase = inst["phase"] * 0.9
    chans = []
    for k, ln in enumerate(inst["local_bones"]):
        if ln.startswith("stem"):
            amp = np.deg2rad(6.0 + 5.0 * k)
            chans.append(_rot(f"{inst['id']}_{ln}", _Z, amp * np.sin(w * t - phase)))
    return chans


def _wing_anim(inst, t, clip):
    if clip != "idle":
        return []
    return [_rot(f"{inst['id']}_arm", _X, np.deg2rad(16.0) * np.sin(_w(3) * t))]


def _spine_anim(inst, t, clip):
    if clip != "idle":
        return []
    names = inst["local_bones"]
    mid = names[len(names) // 2]
    return [_rot(f"{inst['id']}_{mid}", _Z, np.deg2rad(1.5) * np.sin(_w(1) * t))]


def _head_anim(inst, t, clip):
    """V4: a maw head's lower ``jaw`` rotates open then closed (bark / roar)."""
    if clip != "mouth_open" or "jaw" not in inst["local_bones"]:
        return []
    # 0 → open → closed over the clip; about -Z drops the chin (tail at +X) down.
    angle = np.deg2rad(24.0) * (0.5 - 0.5 * np.cos(_w(2) * t))
    return [_rot(f"{inst['id']}_jaw", _Z, -angle)]


def _eyes_anim(inst, t, clip):
    """V4: the sclera bones rotate (pupils ride them) so the gaze sweeps side to side."""
    if clip != "eye_look":
        return []
    angle = np.deg2rad(18.0) * np.sin(_w(1) * t)
    return [_rot(f"{inst['id']}_{ln}", _Y, angle)
            for ln in inst["local_bones"] if ln in ("eye_l", "eye_r")]


_ANIMATORS = {
    "tentacle": _chain_anim,
    "tail": _chain_anim,
    "eyestalk": _eyestalk_anim,
    "wing": _wing_anim,
    "spine": _spine_anim,
    "body": _spine_anim,
    "head": _head_anim,
    "eyes": _eyes_anim,
}


def animate_recipe(recipe, spec, clips=("idle", "mouth_open", "eye_look")) -> list:
    """Build AnimClips for a recipe by summing per-module contributions. A clip is
    emitted only if some module contributes to it, so faceless/jawless creatures
    simply don't carry ``eye_look``/``mouth_open``."""
    _, meta = assemble_with_meta(recipe, spec)
    t = _times()
    out = []
    for clip_name in clips:
        channels = []
        for inst in meta:
            animator = _ANIMATORS.get(inst["kind"])
            if animator is not None:
                channels.extend(animator(inst, t, clip_name))
        if channels:
            out.append(AnimClip(clip_name, t, channels))
    return out

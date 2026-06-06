"""Canonical animation library + retarget (DESIGN §3 animation, M3).

Clips are authored procedurally as per-joint **rotation** tracks on the canonical
rig. Because every generated skeleton shares the bone topology and rest pose is
identity (see M1), a rotation track rotates its bound vertices about that joint's
head with no remapping — "retarget" across proportions is automatic. Translation
tracks (the walk's root bob) are emitted in world units against the already-scaled
skeleton, so they scale too.

Everything is analytic and deterministic (no RNG, no wall-clock).

Frame: +X forward, +Y up, +Z = animal's left.
  tail wag → about Y; leg fore/aft & head nod/thrust → about Z; body roll → about X.
"""

from __future__ import annotations

import numpy as np

from .spec import Spec
from .types import AnimClip, Bone, Channel

_F = np.float32
_Y = np.array([0.0, 1.0, 0.0])
_Z = np.array([0.0, 0.0, 1.0])

DEFAULT_CLIPS = ("idle", "walk", "tail_wag", "bark_pose")


def _times(period: float, n: int) -> np.ndarray:
    """n loop-seamless samples over [0, period] (endpoint == start for sinusoids)."""
    return np.linspace(0.0, period, n, dtype=np.float64)


def _quat(axis: np.ndarray, angle: np.ndarray) -> np.ndarray:
    """Axis-angle → xyzw unit quaternions. ``angle`` is (T,); returns (T,4)."""
    ax = axis / (np.linalg.norm(axis) + 1e-12)
    half = angle * 0.5
    s = np.sin(half)
    out = np.empty((angle.shape[0], 4), dtype=np.float64)
    out[:, 0] = ax[0] * s
    out[:, 1] = ax[1] * s
    out[:, 2] = ax[2] * s
    out[:, 3] = np.cos(half)
    return out


def _rot(bone: str, axis: np.ndarray, angle: np.ndarray) -> Channel:
    return Channel(bone=bone, path="rotation", values=_quat(axis, angle).astype(_F))


def _body_scale(skel: list[Bone]) -> float:
    """Rough creature height for sizing translation amplitudes."""
    ys = np.array([p[1] for b in skel for p in (b.head, b.tail)])
    return float(ys.max() - ys.min()) or 1.0


# --------------------------------------------------------------------------- #
# Clips
# --------------------------------------------------------------------------- #
def _tail_wag(skel: list[Bone]) -> AnimClip:
    t = _times(0.5, 21)
    w = 2.0 * np.pi / 0.5
    amp = {"tail_01": 0.26, "tail_02": 0.38, "tail_03": 0.52}  # radians, rises to tip
    lag = {"tail_01": 0.0, "tail_02": 0.35, "tail_03": 0.7}
    channels = [_rot(b, _Y, a * np.sin(w * t - lag[b])) for b, a in amp.items()]
    return AnimClip("tail_wag", t, channels)


def _idle(skel: list[Bone]) -> AnimClip:
    t = _times(3.0, 31)
    w = 2.0 * np.pi / 3.0
    breathe = np.sin(w * t)
    channels = [
        _rot("spine_02", _Z, np.deg2rad(1.5) * breathe),
        _rot("neck_01", _Z, np.deg2rad(-1.5) * breathe),
        _rot("head", _Z, np.deg2rad(2.0) * np.sin(w * t + 0.5)),
        _rot("tail_01", _Y, np.deg2rad(4.0) * np.sin(w * t)),
    ]
    return AnimClip("idle", t, channels)


def _gait(skel: list[Bone], name: str, period: float, amp_deg: float, bob_frac: float) -> AnimClip:
    t = _times(period, 25)
    w = 2.0 * np.pi / period
    amp = np.deg2rad(amp_deg)
    swing = np.sin(w * t)
    swing_opp = np.sin(w * t + np.pi)
    # Diagonal gait pairs: (FL, HR) in phase; (FR, HL) anti-phase.
    pairs = {
        "thigh_fl": swing, "thigh_hr": swing,
        "thigh_fr": swing_opp, "thigh_hl": swing_opp,
    }
    channels = [_rot(b, _Z, amp * s) for b, s in pairs.items()]
    # Knee bend: shins flex on the rear part of the swing (rectified, lagging).
    knee = np.deg2rad(amp_deg * 0.6)
    shins = {
        "shin_fl": swing, "shin_hr": swing,
        "shin_fr": swing_opp, "shin_hl": swing_opp,
    }
    for b, s in shins.items():
        channels.append(_rot(b, _Z, -knee * np.clip(s, 0.0, None)))
    # Root vertical bob (twice per cycle), as a translation track = rest + offset.
    root = skel[0]
    base = root.head.astype(np.float64)
    bob = bob_frac * _body_scale(skel)
    ty = base[1] + bob * (np.abs(np.sin(2.0 * w * t)) - 0.5)
    trans = np.tile(base, (t.shape[0], 1))
    trans[:, 1] = ty
    channels.append(Channel("root", "translation", trans.astype(_F)))
    return AnimClip(name, t, channels)


def _walk(skel: list[Bone]) -> AnimClip:
    return _gait(skel, "walk", period=0.8, amp_deg=22.0, bob_frac=0.03)


def _run(skel: list[Bone]) -> AnimClip:
    return _gait(skel, "run", period=0.48, amp_deg=34.0, bob_frac=0.05)


def _bark_pose(skel: list[Bone]) -> AnimClip:
    # Quick head/neck thrust up and back (half-sine over the clip).
    t = _times(0.6, 13)
    pulse = np.sin(np.pi * t / 0.6)  # 0 → 1 → 0
    channels = [
        _rot("neck_01", _Z, np.deg2rad(12.0) * pulse),
        _rot("head", _Z, np.deg2rad(18.0) * pulse),
    ]
    return AnimClip("bark_pose", t, channels)


# --------------------------------------------------------------------------- #
# Biped clips (M6) — target biped bone names (spine/neck/head, arms, legs).
# --------------------------------------------------------------------------- #
def _biped_idle(skel: list[Bone]) -> AnimClip:
    t = _times(3.0, 31)
    w = 2.0 * np.pi / 3.0
    breathe = np.sin(w * t)
    channels = [
        _rot("spine_02", _Z, np.deg2rad(2.0) * breathe),
        _rot("neck_01", _Z, np.deg2rad(-1.5) * breathe),
        _rot("head", _Z, np.deg2rad(2.0) * np.sin(w * t + 0.5)),
        _rot("upperarm_l", _Z, np.deg2rad(4.0) * np.sin(w * t)),
        _rot("upperarm_r", _Z, np.deg2rad(4.0) * np.sin(w * t)),
    ]
    return AnimClip("idle", t, channels)


def _biped_walk(skel: list[Bone]) -> AnimClip:
    t = _times(1.0, 25)
    w = 2.0 * np.pi / 1.0
    amp = np.deg2rad(26.0)
    swing = np.sin(w * t)
    opp = np.sin(w * t + np.pi)
    knee = np.deg2rad(18.0)
    channels = [
        _rot("thigh_l", _Z, amp * swing),
        _rot("thigh_r", _Z, amp * opp),
        _rot("shin_l", _Z, -knee * np.clip(swing, 0.0, None)),
        _rot("shin_r", _Z, -knee * np.clip(opp, 0.0, None)),
        _rot("upperarm_l", _Z, np.deg2rad(18.0) * opp),   # arms counter-swing the legs
        _rot("upperarm_r", _Z, np.deg2rad(18.0) * swing),
    ]
    root = skel[0]
    base = root.head.astype(np.float64)
    bob = 0.02 * _body_scale(skel)
    trans = np.tile(base, (t.shape[0], 1))
    trans[:, 1] = base[1] + bob * (np.abs(np.sin(2.0 * w * t)) - 0.5)
    channels.append(Channel("root", "translation", trans.astype(_F)))
    return AnimClip("walk", t, channels)


_QUAD_BUILDERS = {
    "idle": _idle,
    "walk": _walk,
    "run": _run,
    "tail_wag": _tail_wag,
    "bark_pose": _bark_pose,
}
_BIPED_BUILDERS = {
    "idle": _biped_idle,
    "walk": _biped_walk,
}


def animate(skel: list[Bone], spec: Spec) -> list[AnimClip]:
    """Build the requested clips for this archetype's rig. Props have none."""
    if spec.archetype == "prop":
        return []
    builders = _BIPED_BUILDERS if spec.archetype == "biped" else _QUAD_BUILDERS
    requested = spec.animations or list(DEFAULT_CLIPS)
    clips: list[AnimClip] = []
    for name in requested:
        builder = builders.get(str(name))
        if builder is not None:
            clips.append(builder(skel))
    return clips

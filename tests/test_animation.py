"""M3: canonical clips are well-formed, loop-seamless, and deterministic."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pgap.animation import DEFAULT_CLIPS, animate
from pgap.rng import make_rng
from pgap.skeleton import build_skeleton
from pgap.spec import Spec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _clips():
    spec = Spec.load(FIXTURE)
    skel = build_skeleton(spec, make_rng(spec.seed))
    return spec, skel, {c.name: c for c in animate(skel, spec)}


def test_default_clips_present():
    _, _, clips = _clips()
    assert set(clips) == set(DEFAULT_CLIPS)


def test_quaternions_normalized():
    _, _, clips = _clips()
    for clip in clips.values():
        for ch in clip.channels:
            if ch.path == "rotation":
                norms = np.linalg.norm(ch.values, axis=1)
                assert np.allclose(norms, 1.0, atol=1e-5)


def test_rotation_clips_loop_seamlessly():
    # Periodic clips: last rotation keyframe equals the first (clean loop).
    _, _, clips = _clips()
    for name in ("idle", "walk", "tail_wag"):
        for ch in clips[name].channels:
            if ch.path == "rotation":
                assert np.allclose(ch.values[0], ch.values[-1], atol=1e-5)


def test_tail_wag_targets_tail_bones():
    _, _, clips = _clips()
    bones = {ch.bone for ch in clips["tail_wag"].channels}
    assert bones == {"tail_01", "tail_02", "tail_03"}


def test_tail_wag_actually_moves():
    _, _, clips = _clips()
    ch = clips["tail_wag"].channels[-1]  # tail tip
    # Some keyframe quaternion differs meaningfully from identity rotation.
    assert np.abs(ch.values[:, 1]).max() > 0.05  # y-component of the wag quat


def test_walk_has_root_translation_track():
    _, _, clips = _clips()
    paths = {(ch.bone, ch.path) for ch in clips["walk"].channels}
    assert ("root", "translation") in paths


def test_clips_deterministic():
    spec = Spec.load(FIXTURE)
    a = animate(build_skeleton(spec, make_rng(spec.seed)), spec)
    b = animate(build_skeleton(spec, make_rng(spec.seed)), spec)
    assert [c.name for c in a] == [c.name for c in b]
    for ca, cb in zip(a, b):
        assert np.array_equal(ca.times, cb.times)
        for cha, chb in zip(ca.channels, cb.channels):
            assert np.array_equal(cha.values, chb.values)

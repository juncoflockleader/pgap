"""V2-M3: per-module animation composed into clips."""

from __future__ import annotations

import numpy as np

from pgap.spec import Spec
from pgap.v2.animate import animate_recipe
from pgap.v2.library import beholder_recipe, kraken_recipe, octopus_dragon_recipe


def _spec(name="C", h=80):
    return Spec.from_dict({"name": name, "archetype": "biped", "species": name.lower(),
                           "seed": 5, "triBudget": 10000, "proportions": {"heightCm": h},
                           "material": {"baseColor": "purple"}})


def test_kraken_animates_every_tentacle_segment():
    clips = animate_recipe(kraken_recipe(arms=8), _spec("Kraken"))
    assert [c.name for c in clips] == ["idle"]
    idle = clips[0]
    seg_bones = {ch.bone for ch in idle.channels if "_seg_" in ch.bone}
    assert len(seg_bones) == 48  # 8 tentacles x 6 segments


def test_beholder_animates_eyestalks():
    clips = animate_recipe(beholder_recipe(eyes=8), _spec("Beholder"))
    stems = {ch.bone for ch in clips[0].channels if "_stem" in ch.bone}
    assert len(stems) == 16  # 8 stalks x 2 stems


def test_quaternions_normalized():
    clips = animate_recipe(octopus_dragon_recipe(), _spec("OctopusDragon", 130))
    for ch in clips[0].channels:
        norms = np.linalg.norm(ch.values, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)


def test_clip_loops_seamlessly():
    idle = animate_recipe(kraken_recipe(), _spec("Kraken"))[0]
    for ch in idle.channels:
        assert np.allclose(ch.values[0], ch.values[-1], atol=1e-5)


def test_ring_instances_are_dephased():
    idle = animate_recipe(beholder_recipe(eyes=8), _spec("Beholder"))[0]
    by_bone = {ch.bone: ch.values for ch in idle.channels}
    # Two different eyestalks should not move identically (de-phased by index).
    a = by_bone["stalk_0_stem1"]
    b = by_bone["stalk_3_stem1"]
    assert not np.allclose(a, b, atol=1e-3)


def test_animate_deterministic():
    spec = _spec("Kraken")
    a = animate_recipe(kraken_recipe(), spec)[0]
    b = animate_recipe(kraken_recipe(), spec)[0]
    assert all(np.array_equal(x.values, y.values) for x, y in zip(a.channels, b.channels))

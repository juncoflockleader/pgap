"""Landform synthesis: ridged + domain warp + thermal erosion (per-biome)."""

from __future__ import annotations

import numpy as np

from psl import field, stamps
from psl.spec import BIOMES


def _h(biome, seed=1, res=160, r=0.6):
    return field.height_for_biome(np.random.Generator(np.random.PCG64(seed)), res, biome, r)


def test_every_biome_has_real_relief():
    # regression: erosion must not collapse a biome to a near-constant field.
    for biome in BIOMES:
        h = _h(biome)
        assert h.min() >= 0.0 and h.max() <= 1.0
        assert h.std() > 0.05, f"{biome} too flat (std {h.std():.3f})"


def test_height_is_deterministic():
    for biome in ("snow", "plain", "moon"):
        assert np.array_equal(_h(biome), _h(biome))


def test_erosion_carves_without_flattening():
    rng = np.random.Generator(np.random.PCG64(2))
    rough = field.ridged(rng, 160, octaves=6, base_cells=4)
    eroded = field.thermal_erosion(rough, iterations=10)
    assert eroded.std() > 0.5 * rough.std()      # keeps large-scale structure
    assert np.array_equal(eroded, field.thermal_erosion(rough, iterations=10))


def test_snow_is_rougher_than_plain():
    assert _h("snow").std() > _h("plain").std() * 0.8  # ridged alpine ≳ rolling plain


def test_crater_field_makes_bowls_and_rims():
    base = np.full((128, 128), 0.5)
    h = stamps.crater_field(base, np.random.Generator(np.random.PCG64(1)), count=40)
    assert h.min() < 0.5 - 0.02      # bowls dig below the base
    assert h.max() > 0.5 + 0.004     # rims rise above it
    assert h.std() > 0.02


def test_crater_field_deterministic():
    base = np.full((128, 128), 0.5)
    a = stamps.crater_field(base, np.random.Generator(np.random.PCG64(2)), count=30)
    b = stamps.crater_field(base, np.random.Generator(np.random.PCG64(2)), count=30)
    assert np.array_equal(a, b)


def test_moon_biome_is_cratered():
    h = _h("moon")
    assert h.std() > 0.05            # not flat — the crater field gives it relief


def test_domain_warp_changes_field():
    rng = np.random.Generator(np.random.PCG64(3))
    base = field.fbm(rng, 160, octaves=5)
    wx = field.fbm(rng, 160, octaves=3)
    wy = field.fbm(rng, 160, octaves=3)
    warped = field.domain_warp(base, wx, wy, amp=160 * 0.04)
    assert not np.array_equal(warped, base) and warped.std() > 0.05

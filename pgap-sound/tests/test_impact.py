"""Fast-follow #1: impacts via modal synthesis (material collision sounds)."""

import numpy as np

from psap import render_spec
from psap.impact import IMPACT_PRESETS, MATERIAL_PRESETS
from psap.nl import prompt_to_spec, spec_from_preset


def _spectral_centroid(buf, sr=44100):
    mag = np.abs(np.fft.rfft(buf))
    freqs = np.fft.rfftfreq(buf.size, 1.0 / sr)
    return float((freqs * mag).sum() / (mag.sum() + 1e-9))


def test_all_materials_render_healthy():
    for mat in MATERIAL_PRESETS:
        spec = spec_from_preset(mat, seed=1)
        buf = render_spec(spec)
        assert spec.category == "impact"
        expected = int(round(spec.sample_rate * spec.duration_ms / 1000.0))
        assert buf.size == expected, mat
        assert np.all(np.isfinite(buf)), mat
        assert 0.4 < np.max(np.abs(buf)) <= 1.0, mat


def test_materials_are_spectrally_distinct():
    # glass should be much brighter than wood; metal rings longer than stone.
    cen = {m: _spectral_centroid(render_spec(spec_from_preset(m, seed=1)))
           for m in ("wood", "metal", "glass", "stone")}
    assert cen["glass"] > cen["wood"]
    assert cen["glass"] > cen["stone"]


def test_metal_rings_longer_than_stone():
    def tail_energy(m):
        buf = render_spec(spec_from_preset(m, seed=1))
        half = buf.size // 2
        return float(np.sqrt(np.mean(buf[half:] ** 2)))
    # metal sustains into its second half; stone is nearly silent by then
    assert tail_energy("metal") > tail_energy("stone")


def test_impact_determinism_and_seeded_transient():
    a = render_spec(spec_from_preset("wood", seed=1))
    b = render_spec(spec_from_preset("wood", seed=1))
    assert np.array_equal(a, b)


def test_nl_routes_material_words():
    for prompt, mat in (("a metal clang", "metal"), ("wooden knock", "wood"),
                        ("glass shatter", "glass"), ("a heavy stone thud", "stone")):
        spec = prompt_to_spec(prompt, seed=0)
        assert spec.category == "impact"
        assert spec.graph["material"] == mat, prompt


def test_impact_presets_cover_materials():
    assert set(IMPACT_PRESETS) == set(MATERIAL_PRESETS)

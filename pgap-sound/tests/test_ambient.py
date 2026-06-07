"""Fast-follow #2: ambient loops + seamless looping."""

import numpy as np

from psap import render_spec
from psap.ambient import AMBIENT_PRESETS
from psap.nl import prompt_to_spec, spec_from_preset


def test_all_ambient_presets_render_healthy():
    for preset in AMBIENT_PRESETS:
        spec = spec_from_preset(preset, seed=1)
        buf = render_spec(spec)
        assert spec.category == "ambient"
        expected = int(round(spec.sample_rate * spec.duration_ms / 1000.0))
        assert buf.size == expected, preset
        assert np.all(np.isfinite(buf)), preset
        assert 0.4 < np.max(np.abs(buf)) <= 1.0, preset
        assert np.sqrt(np.mean(buf ** 2)) > 0.02, preset


def test_loop_seam_is_seamless():
    # The wrap transition out[-1] -> out[0] is a genuine consecutive pair of the
    # underlying signal, so its jump must be no worse than the interior diffs.
    for preset in AMBIENT_PRESETS:
        buf = render_spec(spec_from_preset(preset, seed=1))
        wrap = abs(buf[0] - buf[-1])
        interior_max = float(np.max(np.abs(np.diff(buf))))
        assert wrap <= 1.5 * interior_max, f"{preset}: seam {wrap} vs {interior_max}"


def test_tonal_loop_seam_is_tiny():
    # For a tonal bed (hum), a bad (truncated) loop would show a large jump; the
    # crossfade keeps it small.
    buf = render_spec(spec_from_preset("hum", seed=1))
    assert abs(buf[0] - buf[-1]) < 0.05


def test_edges_not_faded_to_zero():
    # Unlike one-shots, loops must NOT be faded to silence at the edges.
    buf = render_spec(spec_from_preset("wind", seed=1))
    assert abs(buf[0]) > 1e-3 and abs(buf[-1]) > 1e-3


def test_nl_routes_ambient_words():
    for prompt, preset in (("howling wind", "wind"), ("steady rain", "rain"),
                           ("a crackling campfire", "fire"), ("a flowing stream", "water"),
                           ("a low drone", "drone")):
        spec = prompt_to_spec(prompt, seed=0)
        assert spec.category == "ambient", prompt


def test_ambient_determinism():
    a = render_spec(spec_from_preset("fire", seed=3))
    b = render_spec(spec_from_preset("fire", seed=3))
    assert np.array_equal(a, b)

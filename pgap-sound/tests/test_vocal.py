"""S3: every creature-vocal preset renders to a non-silent buffer of right length."""

import numpy as np

from psap import render_spec
from psap.nl import spec_from_preset
from psap.vocal import VOCAL_PRESETS


def test_all_vocal_presets_audible_and_correct_length():
    for preset in VOCAL_PRESETS:
        spec = spec_from_preset(preset, seed=1)
        buf = render_spec(spec)
        expected = int(round(spec.sample_rate * spec.duration_ms / 1000.0))
        assert buf.size == expected, preset
        assert np.max(np.abs(buf)) > 0.5, f"{preset} too quiet"
        assert np.all(np.isfinite(buf)), preset


def test_bark_and_roar_distinct():
    bark = render_spec(spec_from_preset("bark", seed=1))
    roar = render_spec(spec_from_preset("roar", seed=1))
    # different durations + spectral content => clearly different signals
    assert bark.size != roar.size

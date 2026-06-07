"""Golden corpus: every preset across several seeds renders to a healthy signal
(non-silent, non-degenerate, finite, loudness-safe). Catches dead presets."""

import numpy as np

from psap import render_spec
from psap.ambient import AMBIENT_PRESETS
from psap.impact import IMPACT_PRESETS
from psap.nl import spec_from_preset
from psap.sfx import SFX_PRESETS
from psap.vocal import VOCAL_PRESETS

ALL_PRESETS = sorted({*SFX_PRESETS, *VOCAL_PRESETS, *IMPACT_PRESETS, *AMBIENT_PRESETS})


def test_every_preset_every_seed_is_healthy():
    for preset in ALL_PRESETS:
        for seed in (0, 1, 7, 42):
            spec = spec_from_preset(preset, seed=seed)
            buf = render_spec(spec)
            assert np.all(np.isfinite(buf)), f"{preset}/{seed} non-finite"
            assert np.max(np.abs(buf)) > 0.4, f"{preset}/{seed} too quiet"
            assert np.max(np.abs(buf)) <= 1.0, f"{preset}/{seed} clips"
            # not silent in the body: RMS above a floor
            assert np.sqrt(np.mean(buf ** 2)) > 0.02, f"{preset}/{seed} degenerate"

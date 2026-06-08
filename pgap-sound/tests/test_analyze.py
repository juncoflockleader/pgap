"""Analysis-driven synthesis: modal analysis of the CC0 reference impacts."""

from pathlib import Path

import numpy as np

from psap import wav
from psap.analyze import analyze_impact
from psap.impact import MATERIAL_PRESETS

REFS = Path(__file__).resolve().parents[1] / "refs" / "impacts"


def _analyze(name):
    s, sr, _ = wav.read_wav(REFS / f"{name}_000.wav")
    return analyze_impact(s, sr)


def test_modal_analysis_shape():
    for name in ("wood", "metal", "glass"):
        g = _analyze(name)
        assert 60 < g["base_freq"] < 12000, name
        assert 1 <= len(g["partials"]) <= 6, name
        assert g["partials"][0][0] == 1.0          # fundamental ratio is 1
        assert all(d > 0 for _, _, d in g["partials"]), name
        assert 0.1 <= g["transient"] <= 0.5


def test_analysis_is_deterministic():
    a, b = _analyze("metal"), _analyze("metal")
    assert a == b


def test_wood_is_lower_than_glass():
    # measured: wood resonates low, glass high
    assert _analyze("wood")["base_freq"] < _analyze("glass")["base_freq"]


def test_baked_presets_match_measurement():
    # the committed MATERIAL_PRESETS were produced by this analyzer from the refs
    for name in ("wood", "metal", "glass"):
        g = _analyze(name)
        baked = MATERIAL_PRESETS[name]
        assert abs(baked["base_freq"] - g["base_freq"]) < 1.0, name
        assert len(baked["partials"]) == len(g["partials"]), name

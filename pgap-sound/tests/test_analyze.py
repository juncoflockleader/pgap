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


def test_vocal_formant_bank_changes_timbre():
    from psap import render_spec
    from psap.nl import spec_from_preset
    import copy
    s = spec_from_preset("bark", seed=3)
    withf = render_spec(s)
    s2 = spec_from_preset("bark", seed=3)
    s2.graph = copy.deepcopy(s2.graph)
    s2.graph.pop("formants", None)
    without = render_spec(s2)
    assert not np.array_equal(withf, without)  # formant bank actually shapes the source


def test_vocal_analysis_recovers_formants():
    from psap import render_spec
    from psap.nl import spec_from_preset
    from psap.analyze import analyze_vocal
    s = spec_from_preset("bark", seed=3)  # imposed formants ~620/1500/2700
    g = analyze_vocal(render_spec(s), s.sample_rate)
    fs = [f[0] for f in g["formants"]]
    assert len(fs) >= 2
    assert any(abs(f - 620) < 160 for f in fs), fs   # recovers ~F1
    assert g["f0"] > 0 and g["duration_ms"] > 0


def test_vocal_analysis_deterministic():
    from psap import render_spec
    from psap.nl import spec_from_preset
    from psap.analyze import analyze_vocal
    s = spec_from_preset("roar", seed=2)
    buf = render_spec(s)
    assert analyze_vocal(buf, s.sample_rate) == analyze_vocal(buf, s.sample_rate)


def test_baked_presets_match_measurement():
    # the committed MATERIAL_PRESETS were produced by this analyzer from the refs
    for name in ("wood", "metal", "glass"):
        g = _analyze(name)
        baked = MATERIAL_PRESETS[name]
        assert abs(baked["base_freq"] - g["base_freq"]) < 1.0, name
        assert len(baked["partials"]) == len(g["partials"]), name

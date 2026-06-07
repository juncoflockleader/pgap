"""Fast-follow #3: shared effects bus + variant adjectives + chain validation."""

import numpy as np

from psap import render_spec
from psap.capabilities import validate_spec
from psap.effects import EFFECT_NAMES, apply_chain
from psap.nl import prompt_to_spec, spec_from_preset
from psap.rng import make_rng
from psap.spec import SoundSpec

from .helpers import load_fixture


def _dry():
    g = {"wave": "square", "freq": 600, "env": {"decay": 200}}
    return render_spec(SoundSpec(category="sfx", seed=1, duration_ms=300, graph=g))


def test_every_effect_changes_signal_and_stays_finite():
    base = _dry()
    for name in EFFECT_NAMES:
        out = apply_chain(base, 44100, make_rng(1), [{"type": name}])
        assert out.shape == base.shape
        assert np.all(np.isfinite(out))
        assert not np.array_equal(out, base), name


def test_delay_produces_later_echoes():
    # A short blip is gone after ~50 ms; with delay, real energy appears in the
    # late window where the dry signal is silent.
    g = {"wave": "square", "freq": 800, "env": {"decay": 40}}
    common = dict(category="sfx", seed=1, duration_ms=400, graph=g)
    dry = render_spec(SoundSpec(**common))
    wet = render_spec(SoundSpec(**common,
                      effects=[{"type": "delay", "time_ms": 120, "feedback": 0.5, "wet": 0.6}]))
    late = slice(int(wet.size * 0.5), None)
    dry_late = np.sqrt(np.mean(dry[late] ** 2))
    wet_late = np.sqrt(np.mean(wet[late] ** 2))
    assert wet_late > 0.02 and wet_late > 10 * dry_late, (wet_late, dry_late)


def test_reverb_adds_tail():
    g = {"wave": "square", "freq": 500, "env": {"decay": 30}}
    dry = render_spec(SoundSpec(category="sfx", seed=1, duration_ms=800, graph=g))
    wet = render_spec(SoundSpec(category="sfx", seed=1, duration_ms=800, graph=g,
                                effects=[{"type": "reverb", "decay": 0.6, "wet": 0.5}]))
    tail = slice(int(dry.size * 0.6), None)
    assert np.sqrt(np.mean(wet[tail] ** 2)) > np.sqrt(np.mean(dry[tail] ** 2))


def test_effects_are_deterministic():
    spec = load_fixture("laser_reverb")
    assert np.array_equal(render_spec(spec), render_spec(spec))


def test_loop_with_reverb_stays_seamless():
    spec = spec_from_preset("drone", seed=1)
    spec.effects = [{"type": "reverb", "decay": 0.5, "wet": 0.4}]
    buf = render_spec(spec)
    wrap = abs(buf[0] - buf[-1])
    interior_max = float(np.max(np.abs(np.diff(buf))))
    assert wrap <= 1.5 * interior_max, f"seam {wrap} vs {interior_max}"


def test_nl_adjectives_add_effects():
    assert any(e["type"] == "delay" for e in prompt_to_spec("an echoey laser", 0).effects)
    assert any(e["type"] == "reverb"
               for e in prompt_to_spec("a cavernous roar", 0).effects)
    assert any(e["type"] == "distortion"
               for e in prompt_to_spec("a gritty explosion", 0).effects)
    assert any(e["type"] == "chorus" for e in prompt_to_spec("a lush drone", 0).effects)


def test_nl_bright_dark_scale_cutoff():
    bright = prompt_to_spec("a bright laser", 0)
    dark = prompt_to_spec("a dark laser", 0)
    assert bright.graph["filter"]["cutoff"] > dark.graph["filter"]["cutoff"]


def test_reverb_extends_oneshot_duration():
    plain = prompt_to_spec("a laser zap", 0)
    verb = prompt_to_spec("a cavernous laser zap", 0)
    assert verb.duration_ms > plain.duration_ms


def test_validate_fails_closed_on_unknown_effect():
    ok, _ = validate_spec({"category": "sfx", "sample_rate": 44100, "graph": {},
                           "effects": [{"type": "flanger"}]})
    assert not ok
    ok2, _ = validate_spec({"category": "sfx", "sample_rate": 44100, "graph": {},
                            "effects": [{"type": "reverb", "wet": 0.3}]})
    assert ok2

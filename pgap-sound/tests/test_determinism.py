"""S0: same (spec, seed) -> byte-identical WAV; different seed -> different bytes."""

from psap.spec import SoundSpec

from .helpers import load_fixture, render_bytes


def test_fixtures_are_byte_identical_on_rerun():
    for name in ("laser", "coin", "bark", "roar"):
        spec = load_fixture(name)
        assert render_bytes(spec) == render_bytes(spec), f"{name} not deterministic"


def test_seed_changes_noisy_output():
    g = {"wave": "noise", "freq": 200, "noise": 1.0, "env": {"decay": 200}}
    a = render_bytes(SoundSpec(name="N", category="sfx", seed=1, duration_ms=250, graph=g))
    b = render_bytes(SoundSpec(name="N", category="sfx", seed=2, duration_ms=250, graph=g))
    assert a != b


def test_tonal_output_seed_independent():
    # A pure tonal SFX has no stochastic source -> seed must not matter.
    g = {"wave": "square", "freq": 600, "sweep": -200, "env": {"decay": 200}}
    a = render_bytes(SoundSpec(name="T", category="sfx", seed=1, duration_ms=250, graph=g))
    b = render_bytes(SoundSpec(name="T", category="sfx", seed=99, duration_ms=250, graph=g))
    assert a == b

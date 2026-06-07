"""Seeded humanization: variance turns the seed into a 'different take' knob
without breaking determinism."""

import numpy as np

from psap import render_spec
from psap.spec import SoundSpec

from .helpers import render_bytes

# A purely tonal SFX — no noise source, so only `variance` can make the seed bite.
TONAL = {"wave": "square", "freq": 700, "sweep": -300, "env": {"decay": 250},
         "filter": {"cutoff": 5000, "q": 0.7}}


def _spec(seed, variance):
    return SoundSpec(name="T", category="sfx", seed=seed, duration_ms=300,
                     variance=variance, graph=dict(TONAL, env=dict(TONAL["env"]),
                                                   filter=dict(TONAL["filter"])))


def test_variance_zero_is_exact_and_seed_independent():
    # variance 0 => preset is exact; tonal sound ignores the seed (unchanged contract)
    assert render_bytes(_spec(1, 0.0)) == render_bytes(_spec(2, 0.0))


def test_variance_makes_seed_bite_on_tonal_sounds():
    a = render_bytes(_spec(1, 0.3))
    b = render_bytes(_spec(2, 0.3))
    assert a != b, "different seeds should give different takes when variance > 0"


def test_variance_still_deterministic_per_seed():
    assert render_bytes(_spec(7, 0.4)) == render_bytes(_spec(7, 0.4))


def test_varied_takes_stay_healthy():
    for seed in range(6):
        buf = render_spec(_spec(seed, 0.4))
        assert np.all(np.isfinite(buf))
        assert 0.4 < np.max(np.abs(buf)) <= 1.0


def test_describe_path_varies_by_seed_by_default():
    from psap.nl import prompt_to_spec
    a = render_bytes(prompt_to_spec("a laser zap", seed=1))
    b = render_bytes(prompt_to_spec("a laser zap", seed=2))
    assert a != b  # NL defaults variance=0.2, so seeds diverge even for a tonal laser

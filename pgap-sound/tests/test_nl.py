"""S4: deterministic NL inference; fail-closed on the unrecognized."""

import numpy as np

from psap import render_spec
from psap.capabilities import validate_spec
from psap.nl import prompt_to_spec


CASES = {
    "a laser zap": ("sfx", "laser"),
    "a retro coin pickup": ("sfx", "coin"),
    "collect a gem": ("sfx", "pickup"),
    "a powerup jingle": ("sfx", "powerup"),
    "player jump": ("sfx", "jump"),
    "a big explosion": ("sfx", "explosion"),
    "enemy hit": ("sfx", "hit"),
    "ui menu blip": ("ui", "blip"),
    "a dog bark": ("vocal", "bark"),
    "a small dragon growl": ("vocal", None),  # vocal, preset ambiguous-but-vocal
    "an angry roar": ("vocal", "roar"),
    "a tiny bird chirp": ("vocal", "chirp"),
}


def test_prompts_route_to_expected_category():
    for prompt, (cat, _) in CASES.items():
        spec = prompt_to_spec(prompt, seed=0)
        assert spec.category == cat, f"{prompt!r} -> {spec.category}"
        ok, errors = validate_spec(spec.to_dict())
        assert ok, f"{prompt!r}: {errors}"
        assert np.max(np.abs(render_spec(spec))) > 0.3


def test_retro_adds_bitcrush():
    spec = prompt_to_spec("a retro coin pickup", seed=0)
    assert "bitcrush" in spec.graph.get("fx", [])


def test_size_words_scale_pitch():
    big = prompt_to_spec("a big laser", seed=0)
    small = prompt_to_spec("a small laser", seed=0)
    assert big.graph["freq"] < small.graph["freq"]


def test_fail_closed_on_gibberish():
    try:
        prompt_to_spec("xyzzy nonsense", seed=0)
    except ValueError:
        return
    raise AssertionError("expected ValueError on unrecognized prompt")

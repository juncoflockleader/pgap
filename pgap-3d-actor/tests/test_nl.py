"""M7: natural-language prompt → spec inference."""

from __future__ import annotations

from pgap.capabilities import validate_spec
from pgap.nl import prompt_to_spec
from pgap.spec import Spec


def test_golden_retriever_prompt():
    s = prompt_to_spec("a golden retriever with floppy ears that wags its tail and barks")
    assert s["archetype"] == "quadruped" and s["species"] == "dog"
    assert s["traits"]["ears"] == "floppy"
    assert "tail_wag" in s["animations"] and "bark_pose" in s["animations"]
    assert "golden" in s["material"]["baseColor"] and s["material"]["fur"] is True


def test_biped_prompt():
    s = prompt_to_spec("a tall walking robot")
    assert s["archetype"] == "biped"
    assert s["proportions"]["heightCm"] > 180.0  # "tall"
    assert "walk" in s["animations"]


def test_prop_prompt():
    s = prompt_to_spec("a big grey mossy boulder")
    assert s["archetype"] == "prop" and s["species"] == "rock"


def test_unrecognized_prompt_fails_closed():
    s = prompt_to_spec("a steampunk octopus dragon")
    assert s["archetype"] is None
    assert validate_spec(s)["ok"] is False


def test_prompt_is_deterministic():
    a = prompt_to_spec("a small golden dog that wags", seed=42)
    b = prompt_to_spec("a small golden dog that wags", seed=42)
    assert a == b


def test_inferred_spec_builds():
    s = prompt_to_spec("a golden retriever that wags its tail")
    spec = Spec.from_dict(validate_spec(s)["normalized"])
    assert spec.archetype == "quadruped" and spec.tail_bone == "tail_01"

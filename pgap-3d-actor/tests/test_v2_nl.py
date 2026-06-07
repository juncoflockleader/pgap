"""V2-M5: natural-language → recipe inference (strict templates + free compose)."""

from __future__ import annotations

import numpy as np

from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.nl import prompt_to_recipe


def _builds(res):
    spec = Spec.from_dict({"name": res["name"], "archetype": "biped", "species": "x",
                           "seed": res["seed"], "triBudget": 11000,
                           "proportions": {"heightCm": res["heightCm"]},
                           "material": res["material"]})
    _, mesh = build_actor(res["recipe"], spec, make_rng(spec.seed))
    return mesh


def test_winged_lion_human_head_is_sphinx():
    res = prompt_to_recipe("a winged lion with a human head")
    assert res["ok"] and res["template"] == "sphinx"
    assert _builds(res).num_triangles > 0


def test_descriptive_prompts_route_to_templates():
    cases = {
        "a floating eye monster with eyestalks": "beholder",
        "a mermaid": "merfolk",
        "cthulhu rises": "cthulhu",
        "an octopus dragon": "octopus_dragon",
    }
    for prompt, expected in cases.items():
        assert prompt_to_recipe(prompt)["template"] == expected, prompt


def test_size_and_coat_inference():
    res = prompt_to_recipe("a giant purple mermaid")
    assert res["heightCm"] > 175  # "giant"
    assert "purple" in res["material"]["baseColor"]


def test_unrecognized_prompt_fails_closed():
    res = prompt_to_recipe("a quartz crystal cluster")
    assert res["ok"] is False and res["errors"]


def test_free_mode_composes_a_novel_creature():
    res = prompt_to_recipe("a winged humanoid with a fish tail", mode="free")
    assert res["ok"] and res["mode"] == "free"
    kinds = [m["kind"] for m in res["recipe_dict"]["modules"]]
    assert "wing" in kinds and "serpent_tail" in kinds and "fin" in kinds
    assert _builds(res).num_triangles > 0


def test_free_orb_composition():
    res = prompt_to_recipe("a floating orb with eyestalks and tentacles", mode="free")
    assert res["ok"] and res["mode"] == "free"
    kinds = [m["kind"] for m in res["recipe_dict"]["modules"]]
    assert {"orb", "eyestalk", "tentacle"} <= set(kinds)


def test_inference_deterministic():
    a = prompt_to_recipe("a winged lion with a human head")
    b = prompt_to_recipe("a winged lion with a human head")
    assert a["template"] == b["template"] and a["heightCm"] == b["heightCm"]

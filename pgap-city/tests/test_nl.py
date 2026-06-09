"""Prompt -> spec inference (FR9) + capability report completeness (FR8)."""

from psc.capabilities import capabilities
from psc.nl import prompt_to_spec
from psc.pipeline import generate
from psc.spec import validate_spec


def test_prompts_route_to_cells():
    cases = {
        "a rain-soaked cyberpunk downtown": ("futuristic", "cyberpunk"),
        "a quiet japanese town": ("modern", "japan"),
        "a sprawling steampunk metropolis": ("futuristic", "steampunk"),
        "a dense american grid": ("modern", "american"),
    }
    for prompt, (era, culture) in cases.items():
        s = prompt_to_spec(prompt)["spec"]
        assert (s["era"], s["culture"]) == (era, culture), prompt
        assert validate_spec(s)["ok"]                       # always a valid cell


def test_size_and_density_keywords():
    assert prompt_to_spec("a quiet japanese town")["spec"]["sizeBlocks"] == [2, 2]
    assert prompt_to_spec("a sprawling steampunk metropolis")["spec"]["sizeBlocks"] == [7, 7]
    assert prompt_to_spec("a dense american grid")["spec"]["density"] == 0.95
    assert prompt_to_spec("a quiet japanese town")["spec"]["density"] == 0.45


def test_unrecognized_defaults_with_warning():
    r = prompt_to_spec("a place")
    assert r["spec"]["culture"] == "american" and r["warnings"]


def test_prompt_is_deterministic_and_generates(tmp_path):
    a = prompt_to_spec("a neon cyberpunk block", seed=3)["spec"]
    b = prompt_to_spec("a neon cyberpunk block", seed=3)["spec"]
    assert a == b
    manifest, _ = generate(a, tmp_path)
    assert manifest["cell"] == "futuristicxcyberpunk"


def test_capabilities_are_complete():
    cap = capabilities()
    assert len(cap["cells"]) == 4
    assert set(cap["streetNets"]) == {"grid", "fine_grid", "organic", "curved_industrial"}
    assert cap["propKinds"] and "ranges" in cap and "describe" in cap
    assert "RoadNetwork" in cap["implementedRoles"]
    assert any(r.startswith("PropKit") for r in cap["implementedRoles"])

"""Prompt -> spec inference + capability report."""

from pgear.capabilities import capabilities
from pgear.nl import prompt_to_spec
from pgear.pipeline import generate
from pgear.registry import TEMPLATES
from pgear.spec import validate_spec


def test_prompts_route_to_templates():
    cases = {
        "a curved iron sword with a leather grip": ("sword", "curved"),
        "a heavy battleaxe": ("axe", "battle"),
        "a long spear": ("spear", "pike"),
        "a flanged mace": ("mace", "flanged"),
        "a recurve bow": ("bow", "recurve"),
        "a round wooden shield": ("shield", "round"),
        "a crystal staff": ("staff", "gem"),
        "a great claymore": ("greatsword", "straight"),
        "a small dagger": ("dagger", "straight"),
        "a long curved katana": ("katana", "uchigatana"),
        "a slender rapier": ("thrusting_sword", "rapier"),
        "a twinblade with gold ornament": ("twinblade", "balanced"),
        "a crescent halberd": ("halberd", "crescent"),
        "a grave scythe": ("reaper", "grave"),
        "a spiked flail": ("flail", "spiked"),
        "a great hammer": ("hammer", "great"),
        "a golem greatbow": ("greatbow", "golem"),
        "a repeating crossbow": ("crossbow", "repeating"),
        "a ghostflame torch": ("torch", "ghostflame"),
        "a beast claw": ("claw", "beast"),
        "a spiked caestus": ("fist", "spiked"),
        "a golden order sacred seal": ("sacred_seal", "order"),
        "a fire perfume bottle": ("perfume_bottle", "fire"),
        "a tower greatshield": ("shield", "tower"),
    }
    for prompt, (template, variant) in cases.items():
        s = prompt_to_spec(prompt)["spec"]
        assert s["template"] == template, prompt
        assert s["variant"] == variant, (prompt, s["variant"])
        assert validate_spec(s)["ok"]


def test_size_keywords():
    assert prompt_to_spec("a small dagger")["spec"]["size"] == "small"
    assert prompt_to_spec("a huge greatsword")["spec"]["size"] == "huge"


def test_material_string_is_passed_through():
    s = prompt_to_spec("an obsidian dagger with gold inlay")["spec"]
    assert "obsidian" in s["material"] and "gold" in s["material"]


def test_unrecognized_defaults_to_sword_with_warning():
    r = prompt_to_spec("a shiny thing")
    assert r["spec"]["template"] == "sword" and r["warnings"]


def test_prompt_deterministic_and_generates(tmp_path):
    a = prompt_to_spec("a curved bronze scimitar", seed=2)["spec"]
    b = prompt_to_spec("a curved bronze scimitar", seed=2)["spec"]
    assert a == b
    manifest, _ = generate(a, tmp_path)
    assert manifest["template"] == "sword" and manifest["variant"] == "curved"


def test_capabilities_complete():
    cap = capabilities()
    assert set(cap["templates"]) == set(TEMPLATES)
    assert "curved" in cap["templates"]["sword"]["variants"]
    assert "uchigatana" in cap["templates"]["katana"]["variants"]
    assert "thrusting" in cap["templates"]["shield"]["variants"]
    assert cap["materials"] and cap["sizes"] and "describe" in cap
    assert cap["templates"]["shield"]["category"] == "armor"

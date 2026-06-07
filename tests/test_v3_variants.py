"""V3-M0: the part-variant mechanism (kind = slot, variant = form)."""

from __future__ import annotations

from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.nl import prompt_to_recipe
from pgap.v2.recipe import capability_report, recipe_from_dict, validate_recipe
from pgap.v2.registry import build_module, load_template, TEMPLATE_REGISTRY, variant_names


def test_head_kind_has_three_variants():
    assert variant_names("head") == ["humanoid", "draconic", "cephalopod"]
    assert variant_names("wing") == ["bat"]


def test_variants_emit_different_bones():
    humanoid = {b.name for b in build_module("head").bones}
    draconic = {b.name for b in build_module("head", "draconic").bones}
    assert humanoid != draconic
    assert "snout" in draconic and "horn_l" in draconic
    assert "face" in build_module("head", "cephalopod").sockets


def test_legacy_kind_alias_still_resolves():
    a = [b.name for b in build_module("draconic_head").bones]
    b = [b.name for b in build_module("head", "draconic").bones]
    assert a == b


def test_unknown_variant_raises():
    try:
        build_module("head", "griffon")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_grammar_validates_variants_fail_closed():
    good = {"modules": [{"id": "b", "kind": "body"},
                        {"id": "n", "kind": "dragon_neck", "attach": "b.neck"},
                        {"id": "h", "kind": "head", "variant": "draconic", "attach": "n.top"}]}
    assert validate_recipe(good)["ok"]
    bad = {"modules": [{"id": "h", "kind": "head", "variant": "griffon"}]}
    assert not validate_recipe(bad)["ok"]


def test_variant_specific_sockets_enforced():
    # cephalopod head exposes 'face'; humanoid head does not.
    def rec(variant):
        return {"modules": [{"id": "b", "kind": "body"},
                            {"id": "n", "kind": "dragon_neck", "attach": "b.neck"},
                            {"id": "h", "kind": "head", "variant": variant, "attach": "n.top"},
                            {"id": "f", "kind": "tentacle", "attach": "h.face"}]}
    assert validate_recipe(rec("cephalopod"))["ok"]
    assert not validate_recipe(rec("humanoid"))["ok"]


def test_omitted_variant_uses_default():
    rep = validate_recipe({"modules": [{"id": "h", "kind": "head"}]})
    assert rep["ok"]
    recipe = recipe_from_dict({"name": "H", "modules": [{"id": "h", "kind": "head"}]})
    assert recipe.attachments[0].module.kind == "head"


def test_capability_report_lists_variants():
    rep = capability_report()
    assert rep["modules"]["head"]["variants"] == ["humanoid", "draconic", "cephalopod"]
    assert rep["modules"]["head"]["defaultVariant"] == "humanoid"
    assert rep["schemaVersion"].endswith("v2")  # bumped for variants


def test_variant_recipe_builds():
    data = {"name": "DragonHeadBeast", "modules": [
        {"id": "body", "kind": "body"},
        {"id": "neck", "kind": "dragon_neck", "attach": "body.neck"},
        {"id": "head", "kind": "head", "variant": "draconic", "attach": "neck.top"},
        {"id": "leg", "kind": "leg", "attach": "body.shoulder", "mirror": True}]}
    recipe = recipe_from_dict(data)
    spec = Spec.from_dict({"name": "X", "archetype": "biped", "species": "x", "seed": 5,
                           "triBudget": 10000, "proportions": {"heightCm": 120},
                           "material": {"baseColor": "green"}})
    _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
    assert mesh.num_triangles > 0


def test_nl_free_uses_head_variant():
    res = prompt_to_recipe("a horned dragon-headed beast", mode="free")
    head = next(m for m in res["recipe_dict"]["modules"] if m["kind"] == "head")
    assert head["variant"] == "draconic"


def test_no_regression_templates_still_load():
    for name in TEMPLATE_REGISTRY:
        assert len(load_template(name).attachments) >= 1

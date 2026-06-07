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
    assert variant_names("wing")[0] == "bat"  # bat is the default; more added in V3-M1


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


# --- V3-M1: wing variants -------------------------------------------------- #
def test_wing_has_four_variants():
    assert variant_names("wing") == ["bat", "feathered", "membrane", "insect"]


def test_wing_variants_emit_distinct_bones():
    sets = {v: {b.name for b in build_module("wing", v).bones}
            for v in ("bat", "feathered", "membrane", "insect")}
    assert "web1" in sets["bat"]                       # webbed fingers
    assert any(n.startswith("feather_") for n in sets["feathered"])
    assert "le" in sets["membrane"]                    # leading-edge delta
    assert {"upper", "lower"} <= sets["insect"]
    # all four are different
    assert len({frozenset(s) for s in sets.values()}) == 4


def _winged(variant):
    return {"name": f"W{variant}", "modules": [
        {"id": "body", "kind": "body"},
        {"id": "wing", "kind": "wing", "variant": variant, "attach": "body.wings", "mirror": True}]}


def test_each_wing_variant_builds_valid():
    spec = Spec.from_dict({"name": "W", "archetype": "biped", "species": "x", "seed": 5,
                           "triBudget": 10000, "proportions": {"heightCm": 130},
                           "material": {"baseColor": "teal"}})
    for variant in ("bat", "feathered", "membrane", "insect"):
        recipe = recipe_from_dict(_winged(variant))
        _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
        assert mesh.num_triangles > 0
        import numpy as np
        assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5)


def test_nl_infers_wing_variant():
    assert _wing_variant_of("a dragon with feathered wings") == "feathered"
    assert _wing_variant_of("a fairy with insect wings") == "insect"
    assert _wing_variant_of("a beast with leathery glider wings") == "membrane"
    assert _wing_variant_of("a dragon with wings") == "bat"  # default


def _wing_variant_of(prompt):
    res = prompt_to_recipe(prompt, mode="free")
    wing = next(m for m in res["recipe_dict"]["modules"] if m["kind"] == "wing")
    return wing.get("variant", "bat")


def test_capability_report_lists_wing_variants():
    rep = capability_report()
    assert rep["modules"]["wing"]["variants"] == ["bat", "feathered", "membrane", "insect"]


# --- V3-M2: horn slot + variants ------------------------------------------- #
def test_horn_slot_has_five_variants():
    assert set(variant_names("horn")) == {"unicorn", "antler", "ram", "bull", "rhino"}
    rep = capability_report()
    assert "horn" in rep["modules"]
    assert "horns" in rep["modules"]["head"]["sockets"]  # head.horns socket


def test_horn_variants_emit_distinct_bones():
    counts = {v: len(build_module("horn", v).bones) for v in variant_names("horn")}
    assert counts["unicorn"] == 1 and counts["rhino"] == 1  # single horns
    assert counts["antler"] == 6  # branching pair (beam + 2 tines, bilateral)
    assert counts["ram"] == 6 and counts["bull"] == 4


def test_each_horn_variant_builds():
    spec = Spec.from_dict({"name": "H", "archetype": "biped", "species": "x", "seed": 5,
                           "triBudget": 8000, "proportions": {"heightCm": 60},
                           "material": {"baseColor": "white"}})
    for v in variant_names("horn"):
        recipe = recipe_from_dict({"name": "H", "modules": [{"id": "h", "kind": "horn", "variant": v}]})
        _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
        assert mesh.num_triangles > 0


def test_unicorn_and_stag_templates_build():
    for name in ("unicorn", "stag"):
        recipe = load_template(name)
        spec = Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": 5,
                               "triBudget": 11000, "proportions": {"heightCm": 150},
                               "material": {"baseColor": "white"}})
        skel, mesh = build_actor(recipe, spec, make_rng(spec.seed))
        names = {b.name for b in skel}
        assert any("horn" in n or "beam" in n for n in names)  # the horn slot is present
        assert mesh.num_triangles > 0


def test_nl_unicorn_and_horns():
    assert prompt_to_recipe("a unicorn")["template"] == "unicorn"
    assert prompt_to_recipe("a deer with antlers")["template"] == "stag"
    # free: a horned beast composes a horn module
    res = prompt_to_recipe("a four-legged beast with a unicorn horn", mode="free")
    assert any(m["kind"] == "horn" for m in res["recipe_dict"]["modules"])


# --- V3-M3: tusks / ears / hooves / claws / manes -------------------------- #
def test_new_slots_registered_with_sockets():
    rep = capability_report()
    assert variant_names("ear") == ["floppy", "pointy", "bat", "long"]
    assert set(variant_names("tusk")) == {"boar", "elephant", "walrus"}
    for k in ("hoof", "claw", "mane"):
        assert k in rep["modules"]
    assert {"ears", "tusks"} <= set(rep["modules"]["head"]["sockets"])
    assert "tip" in rep["modules"]["leg"]["sockets"]
    assert "mane" in rep["modules"]["neck"]["sockets"]


def test_new_detail_modules_build():
    spec = Spec.from_dict({"name": "D", "archetype": "biped", "species": "x", "seed": 5,
                           "triBudget": 8000, "proportions": {"heightCm": 60},
                           "material": {"baseColor": "brown"}})
    for kind in ("ear", "tusk", "hoof", "claw", "mane"):
        recipe = recipe_from_dict({"name": "D", "modules": [{"id": "m", "kind": kind}]})
        _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
        assert mesh.num_triangles > 0


def test_boar_horse_feline_build_with_details():
    counts = {}
    for name in ("boar", "horse", "feline"):
        recipe = load_template(name)
        spec = Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": 5,
                               "triBudget": 11000, "proportions": {"heightCm": 120},
                               "material": {"baseColor": "brown"}})
        skel, mesh = build_actor(recipe, spec, make_rng(spec.seed))
        names = [b.name for b in skel]
        counts[name] = names
        assert mesh.num_triangles > 0
    assert any("tusks" in n for n in counts["boar"])
    # hoof/claw applied to all four legs (2 mirror attachments x 2 sides)
    assert sum("hoof" in n for n in counts["horse"]) == 4
    assert sum(n.endswith(("_c0", "_c1", "_c2")) or "claw" in n for n in counts["feline"]) >= 12
    assert any("mane" in n or n.startswith(("mane", "horse_mane")) for n in counts["horse"])


def test_nl_animal_templates_and_free_tusks():
    assert prompt_to_recipe("a wild boar")["template"] == "boar"
    assert prompt_to_recipe("a horse")["template"] == "horse"
    assert prompt_to_recipe("a lion")["template"] == "feline"
    res = prompt_to_recipe("a four-legged beast with tusks and a mane", mode="free")
    kinds = [m["kind"] for m in res["recipe_dict"]["modules"]]
    assert "tusk" in kinds and "mane" in kinds

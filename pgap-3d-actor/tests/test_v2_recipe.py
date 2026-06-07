"""V2-M2: recipe JSON schema, fail-closed grammar validator, capability report."""

from __future__ import annotations

import numpy as np

from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.recipe import capability_report, recipe_from_dict, validate_recipe
from pgap.v2.registry import TEMPLATE_REGISTRY, load_template

_VALID = {
    "name": "JsonBeholder",
    "modules": [
        {"id": "orb", "kind": "orb", "params": {"eye_ring": 6}},
        {"id": "eye", "kind": "eyeball", "attach": "orb.front"},
        {"id": "stalk", "kind": "eyestalk", "attach": "orb.eyes_ring"},
    ],
}


def test_valid_recipe_passes():
    assert validate_recipe(_VALID)["ok"]


def test_unknown_module_kind_fails_closed():
    bad = {"modules": [{"id": "a", "kind": "griffon"}]}
    rep = validate_recipe(bad)
    assert not rep["ok"] and any("griffon" in e for e in rep["errors"])


def test_missing_socket_fails_closed():
    bad = {"modules": [{"id": "orb", "kind": "orb"},
                       {"id": "e", "kind": "eyeball", "attach": "orb.nose"}]}
    rep = validate_recipe(bad)
    assert not rep["ok"] and any("nose" in e for e in rep["errors"])


def test_dangling_parent_fails_closed():
    bad = {"modules": [{"id": "orb", "kind": "orb"},
                       {"id": "e", "kind": "eyeball", "attach": "ghost.front"}]}
    assert not validate_recipe(bad)["ok"]


def test_root_count_enforced():
    no_root = {"modules": [{"id": "orb", "kind": "orb", "attach": "x.y"}]}
    assert not validate_recipe(no_root)["ok"]
    two_root = {"modules": [{"id": "a", "kind": "orb"}, {"id": "b", "kind": "orb"}]}
    assert not validate_recipe(two_root)["ok"]


def test_duplicate_id_fails():
    bad = {"modules": [{"id": "a", "kind": "orb"}, {"id": "a", "kind": "eyeball", "attach": "a.front"}]}
    assert not validate_recipe(bad)["ok"]


def test_unknown_param_warns_not_fails():
    spec = {"modules": [{"id": "orb", "kind": "orb", "params": {"bogus": 3}}]}
    rep = validate_recipe(spec)
    assert rep["ok"] and any("bogus" in w for w in rep["warnings"])


def test_recipe_from_dict_builds_valid_mesh():
    recipe = recipe_from_dict(_VALID)
    spec = Spec.from_dict({"name": "JsonBeholder", "archetype": "biped", "species": "x",
                           "seed": 9, "triBudget": 10000, "proportions": {"heightCm": 80},
                           "material": {"baseColor": "purple"}})
    skel, mesh = build_actor(recipe, spec, make_rng(spec.seed))
    assert len(skel) == 20  # orb(1) + eye(1) + 6 eyestalks x 3
    assert mesh.num_triangles > 0
    assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5)


def test_capability_report_lists_modules_and_templates():
    rep = capability_report()
    assert "orb" in rep["modules"] and "wing" in rep["modules"]
    assert rep["modules"]["orb"]["sockets"]["eyes_ring"]["ring"] is True
    assert set(rep["templates"]) == set(TEMPLATE_REGISTRY)


def test_all_templates_load():
    for name in TEMPLATE_REGISTRY:
        assert len(load_template(name).attachments) >= 1

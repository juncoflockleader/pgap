"""L4 named presets: griffin / manticore / wyvern / pegasus / hydra / naga /
phoenix / basilisk / chimera — each composed from existing bases + parts."""

from pgap.geometry import mesh_stats
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.nl import prompt_to_recipe
from pgap.v2.registry import TEMPLATE_HEIGHT_CM, TEMPLATE_REGISTRY, load_template

PRESETS = ("griffin", "manticore", "wyvern", "pegasus", "hydra",
           "naga", "phoenix", "basilisk", "chimera")


def _build(name):
    spec = Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": 7,
                           "triBudget": 12000, "proportions": {"heightCm": TEMPLATE_HEIGHT_CM[name]},
                           "material": {"baseColor": "stone"}})
    return build_actor(load_template(name), spec, make_rng(spec.seed)), spec


def _legs(skel):
    return len({b.name.rsplit("_", 1)[0] for b in skel if b.name.endswith("_thigh")})


def test_presets_registered():
    for n in PRESETS:
        assert n in TEMPLATE_REGISTRY and n in TEMPLATE_HEIGHT_CM


def test_presets_build_valid():
    for n in PRESETS:
        (skel, mesh), spec = _build(n)
        st = mesh_stats(mesh)
        assert st["triangles"] > 0 and st["finite"], n
        assert mesh.num_triangles <= spec.tri_budget, n
        assert st["boundary_edges"] < 0.03 * st["triangles"] * 3, n   # watertight
        assert st["nonmanifold_edges"] < 0.03 * st["triangles"] * 3, n
        assert skin_stats(mesh)["unweighted_vertices"] == 0, n


def test_wyvern_is_two_legged_and_winged():
    (skel, _), _ = _build("wyvern")
    assert _legs(skel) == 2                       # a wyvern stands on two legs
    assert any("wing" in b.name for b in skel)


def test_hydra_has_three_heads():
    (skel, _), _ = _build("hydra")
    skulls = [b.name for b in skel if b.name.endswith("_skull")]
    assert len(skulls) == 3, skulls


def test_naga_and_basilisk_are_legless():
    for n in ("naga", "basilisk"):
        (skel, _), _ = _build(n)
        assert _legs(skel) == 0, n


def test_griffin_has_four_legs_and_wings():
    (skel, _), _ = _build("griffin")
    assert _legs(skel) == 4 and any("wing" in b.name for b in skel)


def test_nl_routes_presets():
    cases = {"a griffin": "griffin", "a manticore": "manticore", "a wyvern": "wyvern",
             "a winged horse": "pegasus", "a five-headed hydra": "hydra", "a naga": "naga",
             "a phoenix": "phoenix", "a basilisk": "basilisk", "a chimera": "chimera"}
    for prompt, template in cases.items():
        r = prompt_to_recipe(prompt, seed=5)
        assert r["ok"] and r["template"] == template, (prompt, r.get("template"))

"""New v2 body-plan archetypes: serpent / avian / arachnid / hexapod / centaur."""

import numpy as np

from pgap.geometry import mesh_stats
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.nl import prompt_to_recipe
from pgap.v2.registry import TEMPLATE_HEIGHT_CM, TEMPLATE_REGISTRY, load_template

NEW = ("serpent", "avian", "arachnid", "hexapod", "centaur")


def _build(name):
    spec = Spec.from_dict({"name": name, "archetype": "quadruped",
                           "heightCm": TEMPLATE_HEIGHT_CM[name], "seed": 7,
                           "triBudget": 11000, "material": {"baseColor": "tan"}})
    return build_actor(load_template(name), spec, make_rng(spec.seed)), spec


def test_new_archetypes_registered():
    for name in NEW:
        assert name in TEMPLATE_REGISTRY and name in TEMPLATE_HEIGHT_CM


def test_new_archetypes_build_valid():
    for name in NEW:
        (skel, mesh), spec = _build(name)
        st = mesh_stats(mesh)
        assert st["triangles"] > 0 and st["finite"], name
        assert mesh.num_triangles <= spec.tri_budget, name
        assert st["boundary_edges"] < 0.03 * st["triangles"] * 3, name  # watertight
        assert skin_stats(mesh)["unweighted_vertices"] == 0, name


def test_arachnid_legs_splay_outward():
    # the 8 legs must reach well beyond the body radius (a real radial spider)
    (_, mesh), _ = _build("arachnid")
    r = np.sqrt(mesh.positions[:, 0] ** 2 + mesh.positions[:, 2] ** 2)
    assert r.max() > 0.30, f"legs don't splay: max radius {r.max():.2f}"


def test_serpent_is_long_and_low():
    (_, mesh), _ = _build("serpent")
    ext = mesh.positions.max(0) - mesh.positions.min(0)
    assert ext[0] > ext[1]  # longer (X) than tall (Y)


def test_hexapod_has_six_splayed_legs():
    (skel, mesh), _ = _build("hexapod")
    leg_roots = {b.name.rsplit("_", 1)[0] for b in skel if b.name.endswith("_coxa")}
    assert len(leg_roots) == 6, leg_roots                       # three bilateral pairs
    # legs reach out to both sides (a real splayed insect stance)
    z = mesh.positions[:, 2]
    assert z.max() > 0.15 and z.min() < -0.15, (z.min(), z.max())


def test_centaur_has_humanoid_torso_over_four_legs():
    (skel, mesh), _ = _build("centaur")
    names = {b.name for b in skel}
    assert {"arm_l_upperarm", "arm_r_upperarm"} <= names        # human arms up top
    leg_roots = {b.name.rsplit("_", 1)[0] for b in skel if b.name.endswith("_thigh")}
    assert len(leg_roots) == 4, leg_roots                        # four horse legs
    head = next(b for b in skel if b.name == "head_head")
    backs = [b.head[1] for b in skel if b.name.startswith("body_spine")]
    assert head.head[1] > max(backs) + 0.05                      # torso rises above the back


def test_nl_routes_new_archetypes():
    cases = {"a green snake": "serpent", "a cobra": "serpent",
             "a white bird": "avian", "a hawk": "avian",
             "a brown spider": "arachnid", "a tarantula": "arachnid",
             "a giant ant": "hexapod", "a praying mantis": "hexapod",
             "a centaur": "centaur"}
    for prompt, template in cases.items():
        r = prompt_to_recipe(prompt, seed=5)
        assert r["ok"] and r["template"] == template, (prompt, r.get("template"))

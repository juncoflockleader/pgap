"""L3 slot batch: beak, frill, spikes, shell, gills, whiskers, mandibles,
dorsal fin, stinger — each builds and composes on a host."""

from pgap.geometry import mesh_stats
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.nl import prompt_to_recipe
from pgap.v2.recipe import recipe_from_dict, validate_recipe
from pgap.v2.registry import MODULE_REGISTRY, load_template

# slot kind -> host socket it plugs into
SLOTS = {"beak": "head.jaws", "frill": "head.horns", "whiskers": "head.cheeks",
         "mandibles": "head.jaws", "gills": "neck.gills", "spikes": "body.ridge",
         "shell": "body.ridge", "dorsal_fin": "body.ridge", "stinger": "tail.tip"}


def _spec(n="slot", h=120):
    return Spec.from_dict({"name": n, "archetype": "biped", "species": n, "seed": 5,
                           "triBudget": 11000, "proportions": {"heightCm": h},
                           "material": {"baseColor": "tan"}})


def _host(attach):
    base = attach.split(".")[0]
    return {
        "head": [{"id": "body", "kind": "body"},
                 {"id": "neck", "kind": "neck", "attach": "body.neck"},
                 {"id": "head", "kind": "head", "attach": "neck.top"}],
        "neck": [{"id": "body", "kind": "body"},
                 {"id": "neck", "kind": "neck", "attach": "body.neck"}],
        "body": [{"id": "body", "kind": "body"},
                 {"id": "leg", "kind": "leg", "attach": "body.shoulder", "mirror": True}],
        "tail": [{"id": "body", "kind": "body"},
                 {"id": "tail", "kind": "serpent_tail", "attach": "body.tail"}],
    }[base]


def test_all_slots_registered():
    for k in SLOTS:
        assert k in MODULE_REGISTRY, k


def test_slots_build_and_compose_on_a_host():
    for k, attach in SLOTS.items():
        mods = _host(attach) + [{"id": "slot", "kind": k, "attach": attach}]
        report = validate_recipe({"name": k, "modules": mods})
        assert report["ok"], (k, report["errors"])
        skel, mesh = build_actor(recipe_from_dict({"name": k, "modules": mods}), _spec(k), make_rng(5))
        st = mesh_stats(mesh)
        assert st["triangles"] > 0 and st["finite"], k
        assert mesh.num_triangles <= 11000, k
        assert st["boundary_edges"] < 0.03 * st["triangles"] * 3, k     # watertight
        assert st["nonmanifold_edges"] < 0.03 * st["triangles"] * 3, k
        assert skin_stats(mesh)["unweighted_vertices"] == 0, k
        assert any(b.name.startswith("slot_") for b in skel), k          # the slot landed


def test_presets_wear_their_slots():
    expect = {"griffin": "beak_upper", "avian": "beak_upper",
              "phoenix": "beak_upper", "manticore": "stinger_bulb",
              "dragon": "spikes_spike_0"}
    for name, bone in expect.items():
        skel, _ = build_actor(load_template(name), _spec(name), make_rng(5))
        assert bone in {b.name for b in skel}, (name, bone)


def test_nl_routes_slots_in_free_mode():
    cases = {"a spiky dragon": "spikes", "a turtle beast": "shell",
             "a whiskered wolf": "whiskers", "a shark beast": "dorsal_fin",
             "a beaked lizard": "beak"}
    for prompt, kind in cases.items():
        r = prompt_to_recipe(prompt, mode="free")
        kinds = {m["kind"] for m in r.get("recipe_dict", {}).get("modules", [])}
        assert r["ok"] and kind in kinds, (prompt, kinds)

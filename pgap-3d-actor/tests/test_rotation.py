"""Per-attachment rotation in the v2 assembler — pivots a module about its socket.

Zero rotation must be a byte-exact no-op (so every existing creature is unchanged);
a non-zero rotation swings the part about the socket; a mirrored attachment stays
Z-symmetric; the recipe grammar validates the field; and the hydra's heads fan.
"""

import numpy as np

from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.assembly import assemble_recipe, build_actor
from pgap.v2.recipe import recipe_from_dict, validate_recipe
from pgap.v2.registry import load_template


def _spec(h=160):
    return Spec.from_dict({"name": "r", "archetype": "biped", "species": "r", "seed": 5,
                           "triBudget": 11000, "proportions": {"heightCm": h},
                           "material": {"baseColor": "stone"}})


def _bones(modules):
    recipe = recipe_from_dict({"name": "r", "modules": modules})
    return {b.name: b for b in assemble_recipe(recipe, _spec())}


def test_zero_rotation_is_a_noop():
    base = [{"id": "spine", "kind": "spine"},
            {"id": "head", "kind": "head", "variant": "draconic", "attach": "spine.neck"}]
    rot = [{"id": "spine", "kind": "spine"},
           {"id": "head", "kind": "head", "variant": "draconic", "attach": "spine.neck",
            "rotation": [0, 0, 0]}]
    a, b = _bones(base), _bones(rot)
    for k in a:
        assert np.array_equal(a[k].head, b[k].head) and np.array_equal(a[k].tail, b[k].tail), k


def test_yaw_rotates_about_the_socket():
    straight = _bones([{"id": "spine", "kind": "spine"},
                       {"id": "head", "kind": "head", "variant": "draconic", "attach": "spine.neck"}])
    yawed = _bones([{"id": "spine", "kind": "spine"},
                    {"id": "head", "kind": "head", "variant": "draconic", "attach": "spine.neck",
                     "rotation": [60, 0, 0]}])
    # the snout points +X; yaw swings it off the midline, while the socket-side skull
    # head (the pivot) barely moves
    assert abs(straight["head_snout"].tail[2]) < 1e-6
    assert abs(yawed["head_snout"].tail[2]) > 0.05
    assert np.allclose(yawed["head_skull"].head, straight["head_skull"].head, atol=1e-9)


def test_mirror_rotation_stays_symmetric():
    b = _bones([{"id": "body", "kind": "body"},
                {"id": "wing", "kind": "wing", "attach": "body.wings", "mirror": True,
                 "rotation": [20, 10, 0]}])
    l, r = b["wing_l_arm"], b["wing_r_arm"]
    assert np.allclose(l.tail[0], r.tail[0]) and np.allclose(l.tail[1], r.tail[1])
    assert np.allclose(l.tail[2], -r.tail[2])          # a clean Z reflection


def test_bad_rotation_fails_validation():
    rep = validate_recipe({"name": "x", "modules": [
        {"id": "s", "kind": "spine"},
        {"id": "h", "kind": "head", "attach": "s.neck", "rotation": [1, 2]}]})
    assert not rep["ok"]


def test_hydra_heads_fan_out():
    skel, _ = build_actor(load_template("hydra"), _spec(), make_rng(5))
    zs = sorted(float(b.head[2]) for b in skel if b.name.endswith("_skull"))
    assert len(zs) == 3 and (zs[-1] - zs[0]) > 0.5    # fanned, not clustered

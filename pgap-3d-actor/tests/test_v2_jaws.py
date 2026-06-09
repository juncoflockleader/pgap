"""V2 jaws generalization (roadmap 2, B0 — static jaws on every head).

The v1 dog grew a black nose + a dark mouth line on the *primitive* path; this
generalizes them onto the v2/v3 *bone* path, reusing the same ``fused``/``region``
capability the eyes use. A ``jaws`` module (proud non-fused nose bead + a fused,
region-tinted mouth line) sits at each head's ``jaws`` socket. Tests lock in: the
module's flags, the socket on every head variant, composition on real heads, and
determinism.
"""

import numpy as np

from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.library import jaws_module
from pgap.v2.recipe import recipe_from_dict
from pgap.v2.registry import MODULE_REGISTRY, TEMPLATE_HEIGHT_CM, load_template


def _spec(name, seed=5, budget=12000, h=120):
    return Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": seed,
                           "triBudget": budget, "proportions": {"heightCm": h},
                           "material": {"baseColor": "golden"}})


def _region_verts(skel, mesh, bone_name, dark=0.32):
    """Indices of dark surface verts whose dominant bone is ``bone_name``."""
    names = [b.name for b in skel]
    if bone_name not in names:
        return np.empty(0, dtype=int)
    dom = mesh.joints[np.arange(mesh.num_vertices), np.argmax(mesh.weights, axis=1)]
    lum = mesh.colors[:, :3].mean(axis=1)
    return np.nonzero((dom == names.index(bone_name)) & (lum < dark))[0]


# --------------------------------------------------------------------------- #
# Module: a proud non-fused nose + a fused, region-tinted mouth line.
# --------------------------------------------------------------------------- #
def test_jaws_module_flags():
    mod = jaws_module()
    by = {b.name: b for b in mod.bones}
    assert set(by) == {"nose", "mouth"}
    assert by["nose"].fused is False and by["nose"].region == "nose"   # proud bead
    assert by["mouth"].fused is True and by["mouth"].region == "mouth"  # tints, no bulge
    # the mouth is a side-to-side line (spans Z); the nose sits above it
    assert by["mouth"].head[2] > 0 > by["mouth"].tail[2]
    assert by["nose"].head[1] > by["mouth"].head[1]


def test_jaws_lipped_variant_drops_the_nose():
    mod = jaws_module(nose=False)
    assert [b.name for b in mod.bones] == ["mouth"]


# --------------------------------------------------------------------------- #
# Composition: a midline nose + mouth on every head variant.
# --------------------------------------------------------------------------- #
def _head_with_jaws(head_variant, **params):
    spec = _spec(f"head_{head_variant}")
    recipe = recipe_from_dict({"name": "H", "modules": [
        {"id": "spine", "kind": "spine"},
        {"id": "neck", "kind": "neck", "attach": "spine.neck"},
        {"id": "head", "kind": "head", "variant": head_variant, "attach": "neck.top"},
        {"id": "jaws", "kind": "jaws", "attach": "head.jaws", "params": params}]})
    skel, mesh = build_actor(recipe, spec, make_rng(spec.seed))
    return skel, mesh


def test_jaws_socket_on_every_head_variant():
    # the maw head carries its own hinged jaw (V4), so it has no jaws socket.
    sizes = {"humanoid": {}, "draconic": {"radius": 0.020, "width": 0.035},
             "cephalopod": {"radius": 0.016, "width": 0.028}}
    for hv in sizes:
        skel, mesh = _head_with_jaws(hv, **sizes[hv])
        nose = _region_verts(skel, mesh, "jaws_nose")
        mouth = _region_verts(skel, mesh, "jaws_mouth")
        assert len(mouth) >= 6, (hv, "mouth", len(mouth))
        assert len(nose) >= 1, (hv, "nose", len(nose))
        # the mouth is a line centered on the midline: spans both sides, mean ~0
        mz = mesh.positions[mouth, 2]
        assert mz.min() < 0 < mz.max() and abs(mz.mean()) < 0.02, (hv, float(mz.mean()))
        # the nose rides above the mouth line, on the midline
        assert abs(mesh.positions[nose, 2].mean()) < 0.02, hv
        assert mesh.positions[nose, 1].mean() > mesh.positions[mouth, 1].mean(), hv


def test_named_templates_have_a_mouth():
    # Every head-bearing preset gains a dark, midline mouth line.
    for name in ("biped", "dragon", "unicorn", "sphinx", "horse", "feline",
                 "stag", "boar", "serpent", "merfolk"):
        spec = _spec(name, h=TEMPLATE_HEIGHT_CM[name])
        skel, mesh = build_actor(load_template(name), spec, make_rng(spec.seed))
        mouth = _region_verts(skel, mesh, "jaws_mouth")
        assert len(mouth) >= 6, (name, len(mouth))
        # a midline line: present on both sides, centered (mean ~0)
        mz = mesh.positions[mouth, 2]
        assert mz.min() < 0 < mz.max() and abs(mz.mean()) < 0.02, (name, float(mz.mean()))


def test_avian_is_beaked():
    # The bird preset wears a beak slot (L3) instead of a nose/mouth jaws.
    spec = _spec("avian", h=TEMPLATE_HEIGHT_CM["avian"])
    skel, _ = build_actor(load_template("avian"), spec, make_rng(spec.seed))
    names = {b.name for b in skel}
    assert {"beak_upper", "beak_lower"} <= names
    assert "jaws_nose" not in names and "jaws_mouth" not in names


def test_v2_jaws_deterministic():
    a = build_actor(load_template("dragon"), _spec("dragon", h=140), make_rng(5))[1]
    b = build_actor(load_template("dragon"), _spec("dragon", h=140), make_rng(5))[1]
    assert np.array_equal(a.positions, b.positions)
    assert np.array_equal(a.colors, b.colors)

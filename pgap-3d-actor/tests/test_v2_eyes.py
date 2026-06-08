"""V2 eyes generalization (roadmap 2, L1 E1/E2).

The v2/v3 modular path builds organs from *bones*, not extra primitives, so the
non-fused / region capability had to grow onto the bone path too. These tests
lock in: (1) non-fused bones sit proud, (2) bone ``region`` colors independently,
(3) the ``eyes`` module + socket compose a dark, symmetric, proud pair on every
head variant, and (4) it's deterministic.
"""

import numpy as np

from pgap.geometry import build_geometry
from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.types import Bone
from pgap.v2.assembly import build_actor
from pgap.v2.library import eyes_module
from pgap.v2.recipe import recipe_from_dict
from pgap.v2.registry import MODULE_REGISTRY, TEMPLATE_HEIGHT_CM, load_template


def _spec(name, seed=5, budget=11000, h=120):
    return Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": seed,
                           "triBudget": budget, "proportions": {"heightCm": h},
                           "material": {"baseColor": "stone"}})


def _dark_pos(mesh, thresh=0.25):
    """Positions of verts whose painted color is dark (the eyes region)."""
    lum = mesh.colors[:, :3].mean(axis=1)
    return mesh.positions[lum < thresh]


# --------------------------------------------------------------------------- #
# Kernel: non-fused + region now work on bones (the v2 building block).
# --------------------------------------------------------------------------- #
def test_fused_flag_on_bone_reaches_the_kernel():
    # A small bead overlapping a big body. Fused → smooth-min blends it in with a
    # fillet; non-fused → hard-min keeps a distinct crease. The two must differ:
    # this proves the per-bone `fused` flag is threaded into the SDF (the v1 test
    # covers that hard-min reads as a proud, non-melting organ).
    spec = _spec("proud", budget=9000, h=60)
    big = Bone("a", None, np.array([0, 0, 0], np.float32), np.array([0, 0.01, 0], np.float32), 0.10, 0.10)
    bead = lambda fused: Bone("b", None, np.array([0.10, 0, 0], np.float32),
                              np.array([0.102, 0, 0], np.float32), 0.035, 0.035, fused=fused)
    m_fused = build_geometry([big, bead(True)], spec, make_rng(spec.seed))
    m_proud = build_geometry([big, bead(False)], spec, make_rng(spec.seed))
    assert m_fused.num_vertices != m_proud.num_vertices


def test_eyes_module_bones_are_non_fused_and_tagged():
    for variant in ("round", "almond", "slit"):
        mod = eyes_module(variant)
        assert len(mod.bones) == 2, variant            # a mirrored pair
        assert all(not b.fused for b in mod.bones), variant
        assert all(b.region == "eyes" for b in mod.bones), variant
        # one eye each side of the midline (z mirror)
        zs = sorted(b.head[2] for b in mod.bones)
        assert zs[0] < 0 < zs[1], variant


# --------------------------------------------------------------------------- #
# Composition: eyes read as a dark, symmetric, proud pair on real heads.
# --------------------------------------------------------------------------- #
def _build_head_with_eyes(head_variant, eyes_variant="round"):
    spec = _spec(f"head_{head_variant}")
    recipe = recipe_from_dict({"name": "H", "modules": [
        {"id": "spine", "kind": "spine"},
        {"id": "neck", "kind": "neck", "attach": "spine.neck"},
        {"id": "head", "kind": "head", "variant": head_variant, "attach": "neck.top"},
        {"id": "eyes", "kind": "eyes", "variant": eyes_variant, "attach": "head.eyes"}]})
    _, mesh = build_actor(recipe, spec, make_rng(spec.seed))
    return mesh


def test_eyes_socket_on_every_head_variant():
    # Every head variant exposes an `eyes` socket and yields a dark, symmetric pair.
    for hv in MODULE_REGISTRY["head"].variants:
        mesh = _build_head_with_eyes(hv)
        pos = _dark_pos(mesh)
        assert len(pos) >= 8, (hv, len(pos))
        left = (pos[:, 2] > 0.003).sum()
        right = (pos[:, 2] < -0.003).sum()
        assert left >= 3 and right >= 3, (hv, left, right)
        # eyes sit in the upper half of the figure (on the head, not the torso)
        assert pos[:, 1].mean() > 0.5 * mesh.positions[:, 1].max(), hv


def test_every_eyes_variant_composes_on_a_head():
    for ev in MODULE_REGISTRY["eyes"].variants:
        mesh = _build_head_with_eyes("humanoid", ev)
        assert len(_dark_pos(mesh)) >= 8, ev


def test_named_templates_have_eyes():
    # Every head-bearing preset gains a visible, symmetric pair of eyes.
    for name in ("biped", "dragon", "unicorn", "sphinx", "cthulhu", "serpent",
                 "avian", "horse", "arachnid"):
        spec = _spec(name, h=TEMPLATE_HEIGHT_CM[name])
        _, mesh = build_actor(load_template(name), spec, make_rng(spec.seed))
        pos = _dark_pos(mesh)
        assert len(pos) >= 6, (name, len(pos))
        assert (pos[:, 2] > 0.003).sum() >= 2 and (pos[:, 2] < -0.003).sum() >= 2, name


def test_v2_eyes_deterministic():
    a = _build_head_with_eyes("humanoid", "slit")
    b = _build_head_with_eyes("humanoid", "slit")
    assert np.array_equal(a.positions, b.positions)
    assert np.array_equal(a.colors, b.colors)

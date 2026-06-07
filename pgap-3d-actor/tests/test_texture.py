"""M4: UVs, vertex colors, and the procedural golden-fur texture."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pgap import palette
from pgap.pipeline import build_actor
from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.texture import synth_textures

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _spec():
    return Spec.load(FIXTURE)


# --- UV + vertex color (on the mesh) -------------------------------------- #
def test_uvs_present_and_in_range():
    spec = _spec()
    _, mesh = build_actor(spec, make_rng(spec.seed))
    assert mesh.uvs is not None and mesh.uvs.shape == (mesh.num_vertices, 2)
    assert mesh.uvs.min() >= 0.0 and mesh.uvs.max() <= 1.0


def test_vertex_colors_present():
    spec = _spec()
    _, mesh = build_actor(spec, make_rng(spec.seed))
    assert mesh.colors is not None and mesh.colors.shape == (mesh.num_vertices, 4)
    assert np.isfinite(mesh.colors).all()


# --- texture --------------------------------------------------------------- #
def test_basecolor_is_png():
    spec = _spec()
    tex = synth_textures(spec, make_rng(spec.seed))
    assert tex["baseColor"][:8] == b"\x89PNG\r\n\x1a\n"  # PNG signature


def test_texture_deterministic():
    spec = _spec()
    a = synth_textures(spec, make_rng(spec.seed))["baseColor"]
    b = synth_textures(spec, make_rng(spec.seed))["baseColor"]
    assert a == b


def test_material_factors_matte():
    spec = _spec()
    tex = synth_textures(spec, make_rng(spec.seed))
    assert tex["metallicFactor"] == 0.0
    assert tex["roughnessFactor"] >= 0.5  # fur is matte


# --- palette regression ---------------------------------------------------- #
def test_golden_base_is_warm_not_dark():
    # Regression: "darker ears" must not flip the coat to the black palette.
    spec = _spec()
    base = palette.base_coat(spec.material)
    assert base[0] > 0.6 and base[0] > base[2]  # warm: red high, red > blue


def test_region_tints_differ():
    spec = _spec()
    ears = palette.region_color(spec.material, "ears")
    belly = palette.region_color(spec.material, "belly")
    assert ears.sum() < belly.sum()  # ears darker than cream belly


def test_keyword_dispatch():
    mk = lambda s: {"baseColor": s}
    assert tuple(palette.base_coat(mk("jet black lab"))) < tuple(palette.base_coat(mk("golden")))
    assert palette.base_coat(mk("chocolate brown")).sum() < palette.base_coat(mk("cream")).sum()

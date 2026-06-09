"""Building skins: facade/roof texture synthesis + the textured kit glTF."""

import json

import numpy as np

from psc import facade, gltf
from psc.pipeline import generate
from psc.styles import facade_for, profile_for


def _facade(cell, cols=4, rows=5, seed=7):
    fstyle = facade_for(profile_for(*cell))
    return facade.synth_facade(fstyle, cols, rows, np.random.default_rng(seed))


def test_facade_is_deterministic():
    a = _facade(("modern", "american"))[0]
    b = _facade(("modern", "american"))[0]
    assert np.array_equal(a, b)


def test_facade_has_a_window_grid():
    fstyle = facade_for(profile_for("modern", "american"))
    base, normal, _ = _facade(("modern", "american"), cols=4, rows=5)
    # the wall is one color and windows another: several distinct colors, and a
    # meaningful fraction of pixels sit near the glass color (the panes).
    assert base.shape[2] == 3 and base.shape[0] > 0
    glass = np.array(fstyle["glass"])
    near_glass = (np.abs(base.astype(int) - glass).sum(2) < 40).mean()
    assert 0.05 < near_glass < 0.8, near_glass            # windows, not a blank wall
    assert normal.shape == base.shape                     # a matching normal map


def test_cells_have_distinct_skins():
    american = _facade(("modern", "american"))[0]
    cyber = _facade(("futuristic", "cyberpunk"))[0]
    # same grid size → comparable shape; the wall palettes clearly differ
    assert american.mean() > cyber.mean() + 30          # american is light, cyber dark


def test_emissive_only_where_styled():
    assert _facade(("futuristic", "cyberpunk"))[2] is not None   # lit neon windows
    assert _facade(("modern", "american"))[2] is None            # no emissive


def test_building_gltf_is_textured_and_valid():
    fstyle = facade_for(profile_for("futuristic", "cyberpunk"))
    wb, wn, we = facade.synth_facade(fstyle, 4, 6, np.random.default_rng(1))
    rb, rn = facade.synth_roof(fstyle, np.random.default_rng(1))
    from psc.pngio import encode_rgb8
    raw = gltf.building_gltf(encode_rgb8(wb), encode_rgb8(wn), encode_rgb8(rb),
                             encode_rgb8(rn), wall_emissive=encode_rgb8(we), name="SM_t")
    g = json.loads(raw)
    prims = g["meshes"][0]["primitives"]
    assert len(prims) == 2 and len(g["materials"]) == 2      # walls + roof
    assert all("TEXCOORD_0" in p["attributes"] for p in prims)
    assert len(g["images"]) == 5 and len(g["textures"]) == 5
    assert g["samplers"][0]["wrapS"] == 10497                # REPEAT
    assert "emissiveTexture" in g["materials"][0]
    assert "baseColorTexture" in g["materials"][0]["pbrMetallicRoughness"]


def test_pipeline_emits_skinned_kits(tmp_path):
    spec = {"name": "Skin", "era": "modern", "culture": "american",
            "seed": 7, "sizeBlocks": [3, 3]}
    manifest, paths = generate(spec, tmp_path)
    building_meshes = [v for k, v in manifest["roles"].items() if k.startswith("BuildingKit")]
    assert building_meshes
    for name in building_meshes:                            # building kits carry textures
        g = json.loads((tmp_path / name).read_text())
        assert g["images"] and g["textures"]
    # the skin PNGs are written and tracked in the manifest
    base_pngs = list(tmp_path.glob("SM_*_BaseColor.png"))
    assert base_pngs
    assert all(p.name in manifest["files"] for p in base_pngs)


def test_pipeline_still_deterministic(tmp_path):
    spec = {"name": "Skin", "era": "futuristic", "culture": "cyberpunk",
            "seed": 11, "sizeBlocks": [3, 3]}
    m1, _ = generate(spec, tmp_path / "a")
    m2, _ = generate(spec, tmp_path / "b")
    assert m1["files"] == m2["files"]                        # byte-identical SHAs

"""Road network + prop scatter: instances in the layout, kit meshes, instancing."""

import json

import numpy as np

from psc import facade, gltf, network, props
from psc.instancing import instancing_payloads
from psc.pipeline import generate
from psc.styles import facade_for, profile_for


def _layout(cell=("modern", "american"), seed=7):
    return network.generate_layout(profile_for(*cell), [3, 3], seed, 0.7)


def test_layout_has_roads_and_props():
    lay = _layout()
    assert lay["road_instances"] and lay["prop_instances"]
    # one road slab per street segment, kit "road", sized [length, width, thick]
    assert len(lay["road_instances"]) == len(lay["streets"])
    for r in lay["road_instances"]:
        assert r["kit"] == "road" and len(r["scale3"]) == 3
        assert r["scale3"][0] > r["scale3"][1] and r["yaw"] in (0.0, 90.0)
    # props reference per-kind kits
    assert all(p["kit"].startswith("prop_") for p in lay["prop_instances"])


def test_road_kit_is_a_textured_slab():
    fstyle = facade_for(profile_for("modern", "american"))
    rb, rn = facade.synth_road(fstyle, np.random.default_rng(1))
    # a center line (along U) sits at mid-width
    mid = rb[rb.shape[0] // 2]
    assert (np.abs(mid.astype(int) - np.array([235, 200, 60])).sum(1) < 60).any()
    curb = np.full((8, 8, 3), 30, np.uint8)
    from psc.pngio import encode_rgb8
    g = json.loads(gltf.building_gltf(encode_rgb8(curb), encode_rgb8(curb),
                                      encode_rgb8(rb), encode_rgb8(rn), name="SM_road"))
    assert len(g["meshes"][0]["primitives"]) == 2 and len(g["images"]) == 4


def test_prop_proxies_build_with_emissive():
    fstyle = facade_for(profile_for("futuristic", "cyberpunk"))
    for kind in ("street_tree", "lamp_post", "neon_sign", "sedan"):
        parts = props.prop_parts(kind, fstyle)
        assert parts and all("color" in p for p in parts)
        g = json.loads(gltf.prop_gltf(parts, name=f"SM_prop_{kind}"))
        assert len(g["meshes"][0]["primitives"]) == len(parts) == len(g["materials"])
        # finite geometry, no textures
        assert "images" not in g and g["accessors"][0]["count"] > 0
    # the neon sign glows
    sign = json.loads(gltf.prop_gltf(props.prop_parts("neon_sign", fstyle), name="x"))
    assert any("emissiveFactor" in m for m in sign["materials"])


def test_instancing_covers_buildings_roads_props(tmp_path):
    manifest, paths = generate({"name": "C", "era": "futuristic", "culture": "cyberpunk",
                                "seed": 9, "sizeBlocks": [3, 3]}, tmp_path, handoff=True)
    bundle = json.loads(paths["instancing"].read_text())
    kinds = {k["kit"] for k in bundle["kits"]}
    assert "road" in kinds and any(k.startswith("prop_") for k in kinds)
    # every referenced kit mesh exists on disk
    for k in bundle["kits"]:
        assert (tmp_path / k["meshFile"]).exists()
    assert "RoadNetwork" in manifest["roles"]
    assert any(r.startswith("PropKit:") for r in manifest["roles"])
    assert manifest["pending"] == []                       # roads + props no longer pending


def test_roads_props_deterministic(tmp_path):
    a, _ = generate({"name": "C", "era": "modern", "culture": "japan",
                     "seed": 4, "sizeBlocks": [3, 3]}, tmp_path / "a")
    b, _ = generate({"name": "C", "era": "modern", "culture": "japan",
                     "seed": 4, "sizeBlocks": [3, 3]}, tmp_path / "b")
    assert a["files"] == b["files"]

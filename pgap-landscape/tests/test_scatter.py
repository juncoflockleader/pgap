"""L2: scatter-by-rule — foliage/prop placement derived from the terrain."""

from __future__ import annotations

import json

import numpy as np

from psl import field, generate, scatter, surfacing


def _ctx(biome="forest", seed=4, res=160):
    rng = np.random.Generator(np.random.PCG64(seed))
    h = field.height_for_biome(rng, res, biome, 0.5)
    layers = {"forest": ["grass", "dirt", "rock"], "ocean": ["sand", "rock"]}[biome]
    w, d = surfacing.weightmaps(h, biome, layers, 0.0)
    return h, d, w


def test_scatter_is_deterministic():
    h, d, w = _ctx()
    spec = {"density": 0.4, "species": ["pine", "bush", "boulder"]}
    a = scatter.scatter(h, d, w, "forest", spec, np.random.Generator(np.random.PCG64(1)))
    b = scatter.scatter(h, d, w, "forest", spec, np.random.Generator(np.random.PCG64(1)))
    assert a == b


def test_pines_track_low_slope_grass():
    h, d, w = _ctx()
    out = scatter.scatter(h, d, w, "forest", {"density": 0.5, "species": ["pine"]},
                          np.random.Generator(np.random.PCG64(2)))
    pts = out["points"]["pine"]
    assert len(pts) > 10
    res = d["slope"].shape[0]
    bad = 0
    for u, vv, _h, _yaw, _sc in pts:
        ix, iy = min(res - 1, int(u * res)), min(res - 1, int(vv * res))
        if d["slope"][iy, ix] > 0.40 + 1e-6:   # never on steeper-than-rule ground
            bad += 1
    assert bad == 0, f"{bad} pines on too-steep ground"


def test_points_inside_tile_and_have_scale():
    h, d, w = _ctx()
    out = scatter.scatter(h, d, w, "forest", {"density": 0.4, "species": ["boulder"]},
                          np.random.Generator(np.random.PCG64(3)))
    for u, vv, _h, yaw, sc in out["points"]["boulder"]:
        assert 0.0 <= u <= 1.0 and 0.0 <= vv <= 1.0
        assert 0.0 <= yaw <= 360.0 and 0.7 <= sc <= 1.7


def test_density_scales_count():
    h, d, w = _ctx()
    lo = scatter.scatter(h, d, w, "forest", {"density": 0.15, "species": ["pine"]},
                         np.random.Generator(np.random.PCG64(5)))["counts"]["pine"]
    hi = scatter.scatter(h, d, w, "forest", {"density": 0.7, "species": ["pine"]},
                         np.random.Generator(np.random.PCG64(5)))["counts"]["pine"]
    assert hi > lo


def test_rules_reference_3d_actor_roles():
    h, d, w = _ctx()
    out = scatter.scatter(h, d, w, "forest", {"density": 0.4, "species": ["pine", "boulder"]},
                          np.random.Generator(np.random.PCG64(1)))
    by = {r["species"]: r for r in out["rules"]}
    assert by["boulder"]["role"] == "prop:rock" and by["boulder"]["available"] is True
    assert by["pine"]["source"] == "pgap-3d-actor"


def test_ocean_scatters_nothing():
    h, d, w = _ctx(biome="ocean")
    out = scatter.scatter(h, d, w, "ocean", {"density": 0.4, "species": []},
                          np.random.Generator(np.random.PCG64(1)))
    assert out["rules"] == [] and out["points"] == {}


def test_pipeline_emits_foliage_rule(tmp_path):
    m, paths = generate({"biome": "forest", "name": "F", "resolution": 505, "seed": 4},
                        tmp_path, handoff=True)
    assert "FoliageRule" in m["roles"]
    assert paths["scatter"].exists()
    data = json.loads(paths["scatter"].read_text())
    assert set(data["counts"]) <= {"pine", "bush", "boulder"}
    sc = json.loads(paths["sidecar"].read_text())
    assert sc["scatter"]["points"] == paths["scatter"].name and "rules" in sc["scatter"]

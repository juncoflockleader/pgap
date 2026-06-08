"""L4: ocean/shore water plane + sea-level-derived submersion."""

from __future__ import annotations

import json

from psl import generate


def _sidecar(paths):
    return json.loads(paths["sidecar"].read_text())


def test_ocean_emits_water_plane(tmp_path):
    m, paths = generate({"biome": "ocean", "name": "O", "resolution": 505, "seed": 6},
                        tmp_path, handoff=True)
    w = _sidecar(paths)["water"]
    assert w["enabled"] and w["seaLevelM"] > 0 and w["foam"] and len(w["color"]) == 3
    assert abs(w["submergedFraction"] - 0.62) < 0.03      # mostly sea
    assert "WaterPlane" in m["roles"]
    hand = json.loads(paths["handoff"].read_text())
    assert any(r["role"] == "WaterPlane" for r in hand["roles"])


def test_shore_submerged_target_is_seed_stable(tmp_path):
    for seed in (6, 11, 20):
        _, paths = generate({"biome": "shore", "name": "S", "resolution": 505, "seed": seed},
                            tmp_path / f"s{seed}")
        assert abs(_sidecar(paths)["water"]["submergedFraction"] - 0.32) < 0.03


def test_dry_biomes_have_no_water(tmp_path):
    for b in ("plain", "snow", "moon", "forest"):
        m, paths = generate({"biome": b, "name": b, "resolution": 505}, tmp_path / b)
        assert _sidecar(paths)["water"]["enabled"] is False
        assert "WaterPlane" not in m["roles"]


def test_shore_has_beach_layers(tmp_path):
    _, paths = generate({"biome": "shore", "name": "S", "resolution": 505, "seed": 6}, tmp_path)
    layers = [l["name"] for l in _sidecar(paths)["materialSpec"]["layers"]]
    assert "wetsand" in layers and "sand" in layers


def test_explicit_sea_level_is_respected(tmp_path):
    _, paths = generate({"biome": "ocean", "name": "O", "resolution": 505, "seed": 6,
                         "seaLevel": 0.4}, tmp_path)
    assert abs(_sidecar(paths)["seaLevel"] - 0.4) < 1e-6   # user value not overridden


def test_seaLevel_meters_matches(tmp_path):
    _, paths = generate({"biome": "ocean", "name": "O", "resolution": 505, "seed": 6,
                         "heightScaleM": 500}, tmp_path)
    sc = _sidecar(paths)
    assert abs(sc["water"]["seaLevelM"] - sc["seaLevel"] * 500) < 0.5

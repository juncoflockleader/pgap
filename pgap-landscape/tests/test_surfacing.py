"""L1: rule-based surfacing — weightmaps derived from slope/altitude (PRD §5)."""

from __future__ import annotations

import hashlib

import numpy as np

from psl import field, generate, surfacing


def _height(biome="snow", seed=1, res=128):
    rng = np.random.Generator(np.random.PCG64(seed))
    return field.height_for_biome(rng, res, biome, 0.5)


def test_weightmaps_sum_to_one():
    h = _height()
    w, _ = surfacing.weightmaps(h, "snow", ["snow", "rock", "scree"], 0.0)
    total = sum(w.values())
    assert np.allclose(total, 1.0, atol=1e-4)
    for m in w.values():
        assert m.min() >= 0.0 and m.max() <= 1.0


def test_surfacing_is_coherent_with_terrain():
    h = _height()
    w, d = surfacing.weightmaps(h, "snow", ["snow", "rock", "scree"], 0.0)
    slope, alt = d["slope"], d["altitude"]
    hi_flat = (alt > 0.7) & (slope < 0.2)
    steep = slope > 0.5
    if hi_flat.any() and steep.any():
        # snow accumulates on high+flat, never on cliffs; rock the opposite
        assert w["snow"][hi_flat].mean() > w["snow"][steep].mean()
        assert w["snow"][steep].mean() < 0.05
        assert w["rock"][steep].mean() > w["rock"][hi_flat].mean()


def test_sand_bands_near_sea_level():
    h = _height(biome="shore")
    w, d = surfacing.weightmaps(h, "shore", ["wetsand", "sand", "grass", "rock"], 0.25)
    alt = d["altitude"]
    near = np.abs(alt - 0.25) < 0.04
    far = alt > 0.6
    if near.any() and far.any():
        assert w["sand"][near].mean() > w["sand"][far].mean()


def test_pipeline_emits_weightmaps_and_roles(tmp_path):
    m, paths = generate({"biome": "snow", "name": "S", "resolution": 505, "seed": 2},
                        tmp_path, handoff=True)
    layers = ["snow", "rock", "scree"]
    for layer in layers:
        assert paths[f"weight_{layer}"].exists()
        assert f"Weightmap:{layer}" in m["roles"]
    assert "LandscapeMaterialSpec" in m["roles"]
    # manifest SHAs match the bytes on disk
    for fn, sha in m["files"].items():
        assert hashlib.sha1((tmp_path / fn).read_bytes()).hexdigest() == sha
    assert paths["handoff"].exists()


def test_material_spec_in_sidecar(tmp_path):
    import json
    _, paths = generate({"biome": "plain", "name": "P", "resolution": 505}, tmp_path)
    sc = json.loads(paths["sidecar"].read_text())
    ms = sc["materialSpec"]
    assert ms["blend"] == "weight" and ms["layerOrder"] == sc["layers"]
    for layer in ms["layers"]:
        assert "color" in layer and "weightmap" in layer


def test_weightmaps_deterministic():
    h = _height()
    a, _ = surfacing.weightmaps(h, "snow", ["snow", "rock", "scree"], 0.0)
    b, _ = surfacing.weightmaps(h, "snow", ["snow", "rock", "scree"], 0.0)
    for layer in a:
        assert np.array_equal(a[layer], b[layer])

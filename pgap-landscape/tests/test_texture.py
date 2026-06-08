"""L5: tiling per-layer base-color + normal textures."""

from __future__ import annotations

import json

import numpy as np

from psl import generate, surfacing, texture


def _tex(layer, seed=1):
    return texture.layer_textures(layer, surfacing.layer_color(layer),
                                  np.random.Generator(np.random.PCG64(seed)))


def test_textures_are_rgb_and_tile_seamlessly():
    for layer in texture.LAYER_TEX:
        base, nrm = _tex(layer)
        assert base.shape == (256, 256, 3) and base.dtype == np.uint8
        assert nrm.shape == (256, 256, 3)
        # opposite edges match (periodic) → tiles
        assert np.abs(base[:, 0].astype(int) - base[:, -1].astype(int)).mean() < 8
        assert np.abs(base[0, :].astype(int) - base[-1, :].astype(int)).mean() < 8


def test_normal_map_is_z_dominant():
    _, nrm = _tex("rock")
    assert nrm[:, :, 2].mean() > 150          # tangent-space normal points mostly +Z


def test_base_color_centers_on_layer_color():
    base, _ = _tex("grass")
    mean = base.reshape(-1, 3).mean(axis=0)
    target = np.array(surfacing.layer_color("grass"))
    assert np.abs(mean - target).max() < 30   # modulation centers on the layer color


def test_textures_deterministic_and_distinct():
    a = _tex("grass", 2)
    b = _tex("grass", 2)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert not np.array_equal(_tex("rock")[0], _tex("sand")[0])


def test_pipeline_emits_layer_textures(tmp_path):
    m, paths = generate({"biome": "snow", "name": "S", "resolution": 505, "seed": 3}, tmp_path)
    sc = json.loads(paths["sidecar"].read_text())
    assert sc["materialSpec"]["tiling"] is True
    for layer in sc["materialSpec"]["layers"]:
        assert "baseColor" in layer and "normal" in layer
        assert (tmp_path / layer["baseColor"]).exists()
        assert (tmp_path / layer["normal"]).exists()
        assert layer["baseColor"] in m["files"] and layer["normal"] in m["files"]
    png = (tmp_path / sc["materialSpec"]["layers"][0]["baseColor"]).read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

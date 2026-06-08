"""Determinism + validation smoke (the fixture-SHA invariant for any gen code)."""

from __future__ import annotations

import json

from psl import generate, validate_spec
from psl.capabilities import capabilities


def test_capabilities_lists_biomes():
    c = capabilities()
    assert c["schemaVersion"].startswith("psl.capabilities")
    for b in ("plain", "forest", "snow", "ocean", "shore", "moon"):
        assert b in c["biomes"]


def test_unsupported_biome_fails_closed():
    v = validate_spec({"biome": "lava"})
    assert not v["ok"] and v["errors"]


def test_same_seed_byte_identical(tmp_path):
    spec = {"name": "P", "biome": "plain", "seed": 7, "resolution": 505}
    m1, p1 = generate(spec, tmp_path / "a")
    m2, p2 = generate(spec, tmp_path / "b")
    assert m1["specHash"] == m2["specHash"]
    assert p1["heightmap"].read_bytes() == p2["heightmap"].read_bytes()
    assert m1["files"][p1["heightmap"].name] == m2["files"][p2["heightmap"].name]


def test_seed_changes_output(tmp_path):
    a, pa = generate({"biome": "plain", "seed": 1, "resolution": 505}, tmp_path / "a")
    b, pb = generate({"biome": "plain", "seed": 2, "resolution": 505}, tmp_path / "b")
    assert pa["heightmap"].read_bytes() != pb["heightmap"].read_bytes()


def test_heightmap_is_16bit_png(tmp_path):
    _, p = generate({"biome": "plain", "seed": 0, "resolution": 505}, tmp_path)
    data = p["heightmap"].read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    # IHDR bit-depth byte (offset 24) == 16, color-type (offset 25) == 0 (grayscale)
    assert data[24] == 16 and data[25] == 0
    sidecar = json.loads(p["sidecar"].read_text())
    assert sidecar["resolution"] == 505

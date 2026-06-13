"""Determinism, validation, and smoke coverage for pgap-2d."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from p2d.capabilities import capability_report, validate_spec
from p2d.pipeline import generate
from p2d.background import BIOMES
from p2d.portrait import ARCHETYPES


def test_same_spec_same_seed_byte_identical(tmp_path):
    spec = {"kind": "portrait", "archetype": "slime", "seed": 7, "size": 128}
    generate(spec, tmp_path / "a")
    generate(spec, tmp_path / "b")
    a = (tmp_path / "a" / "slime_portrait_s7.png").read_bytes()
    b = (tmp_path / "b" / "slime_portrait_s7.png").read_bytes()
    assert a == b


def test_different_seed_different_pixels(tmp_path):
    a = generate({"kind": "portrait", "archetype": "bat", "seed": 1, "size": 128}, tmp_path)
    b = generate({"kind": "portrait", "archetype": "bat", "seed": 2, "size": 128,
                  "name": "bat2"}, tmp_path)
    pa = (tmp_path / a["files"][0]["path"]).read_bytes()
    pb = (tmp_path / b["files"][0]["path"]).read_bytes()
    assert pa != pb


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_all_archetypes_render(tmp_path, archetype):
    m = generate({"kind": "portrait", "archetype": archetype, "seed": 0, "size": 128},
                 tmp_path)
    out = tmp_path / m["files"][0]["path"]
    assert out.exists() and out.stat().st_size > 500
    assert m["files"][0]["role"] == "Portrait"


@pytest.mark.parametrize("biome", sorted(BIOMES))
def test_all_biomes_render(tmp_path, biome):
    m = generate({"kind": "background", "biome": biome, "seed": 0,
                  "width": 288, "height": 162}, tmp_path)
    out = tmp_path / m["files"][0]["path"]
    assert out.exists() and out.stat().st_size > 500
    assert m["files"][0]["role"] == "BattleBackdrop"


def test_manifest_written(tmp_path):
    m = generate({"kind": "background", "biome": "night", "seed": 3,
                  "width": 128, "height": 128}, tmp_path)
    manifest = json.loads((tmp_path / "night_bg_s3.manifest.json").read_text())
    assert manifest == m
    assert manifest["schemaVersion"] == 1


def test_validation_fails_closed():
    ok, errs = validate_spec({"kind": "portrait", "archetype": "dragon"})
    assert not ok and any("dragon" in e for e in errs)
    ok, errs = validate_spec({"kind": "background", "biome": "volcano"})
    assert not ok
    ok, errs = validate_spec({"kind": "sprite"})
    assert not ok
    ok, errs = validate_spec({"kind": "portrait", "archetype": "slime", "bogus": 1})
    assert not ok


def test_capability_report_lists_everything():
    cap = capability_report()
    assert set(cap["kinds"]["portrait"]["archetypes"]) == set(ARCHETYPES)
    assert set(cap["kinds"]["background"]["biomes"]) == set(BIOMES)

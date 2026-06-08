"""Determinism + fail-closed smoke for pgap-city (C0 layout grammar)."""

from __future__ import annotations

import json

from psc import CELLS, generate, validate_spec
from psc.capabilities import capabilities


def test_capabilities_lists_four_cells():
    c = capabilities()
    assert c["schemaVersion"].startswith("psc.capabilities")
    cells = set(c["cells"])
    for expected in ("modernxamerican", "modernxjapan", "futuristicxcyberpunk", "futuristicxsteampunk"):
        assert expected in cells


def test_unsupported_cell_fails_closed():
    assert not validate_spec({"era": "medieval", "culture": "european"})["ok"]
    assert not validate_spec({"era": "modern", "culture": "atlantis"})["ok"]


def test_all_v1_cells_generate(tmp_path):
    for era, culture in CELLS:
        m, p = generate({"era": era, "culture": culture, "seed": 1, "sizeBlocks": [2, 2]}, tmp_path / f"{era}_{culture}")
        assert m["counts"]["instances"] >= 1
        layout = json.loads(p["layout"].read_text())
        assert layout["cell"] == f"{era}x{culture}"
        # every instance references a kit that has an emitted mesh
        kits = {k["id"] for k in layout["kits"]}
        assert all(inst["kit"] in kits for inst in layout["instances"])


def test_same_seed_byte_identical(tmp_path):
    spec = {"era": "modern", "culture": "american", "seed": 5, "sizeBlocks": [3, 3]}
    m1, p1 = generate(spec, tmp_path / "a")
    m2, p2 = generate(spec, tmp_path / "b")
    assert m1["specHash"] == m2["specHash"]
    assert p1["layout"].read_bytes() == p2["layout"].read_bytes()


def test_seed_changes_layout(tmp_path):
    a, pa = generate({"era": "modern", "culture": "american", "seed": 1}, tmp_path / "a")
    b, pb = generate({"era": "modern", "culture": "american", "seed": 2}, tmp_path / "b")
    assert pa["layout"].read_bytes() != pb["layout"].read_bytes()

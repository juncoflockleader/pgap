"""Per-kit bulk-instancing payloads for unreal-mcp-rx editor_instances_place."""

from __future__ import annotations

import json

from psc import generate
from psc.instancing import instancing_payloads
from psc.network import generate_layout
from psc.styles import profile_for


def _layout(seed=5):
    layout = generate_layout(profile_for("modern", "american"), [3, 3], seed, 0.7)
    layout["name"] = "T"
    return layout


def test_groups_all_instances_by_kit():
    layout = _layout()
    bundle = instancing_payloads(layout)
    assert bundle["tool"] == "editor_instances_place"
    # buildings + roads + props are all grouped into per-kit HISM payloads
    all_inst = (layout["instances"] + layout.get("road_instances", [])
                + layout.get("prop_instances", []))
    assert bundle["totalInstances"] == len(all_inst)
    assert sum(k["count"] for k in bundle["kits"]) == len(all_inst)
    # one group per distinct kit, mesh file named for it
    kit_ids = {inst["kit"] for inst in all_inst}
    assert {k["kit"] for k in bundle["kits"]} == kit_ids
    for k in bundle["kits"]:
        assert k["meshFile"] == f"SM_{k['kit']}.gltf"


def test_payload_matches_editor_instances_place_shape():
    bundle = instancing_payloads(_layout())
    for k in bundle["kits"]:
        p = k["payload"]
        assert set(p) == {"mesh_path", "hierarchical", "label", "instances"}
        assert p["hierarchical"] is True
        assert p["label"] == f"{k['kit']}_HISM"
        assert len(p["instances"]) == k["count"]
        for t in p["instances"]:
            assert set(t["location"]) == {"x", "y", "z"}
            assert set(t["rotation"]) == {"pitch", "yaw", "roll"}
            assert set(t["scale"]) == {"x", "y", "z"}


def test_transforms_preserve_layout_values():
    layout = _layout()
    bundle = instancing_payloads(layout)
    # index emitted transforms by (kit, x, y) and check one against the layout
    inst0 = layout["instances"][0]
    grp = next(k for k in bundle["kits"] if k["kit"] == inst0["kit"])
    match = next(t for t in grp["payload"]["instances"]
                 if t["location"]["x"] == inst0["x"] and t["location"]["y"] == inst0["y"])
    assert match["rotation"]["yaw"] == inst0["yaw"]
    assert [match["scale"]["x"], match["scale"]["y"], match["scale"]["z"]] == inst0["scale3"]


def test_pipeline_emits_instancing_role(tmp_path):
    m, paths = generate({"name": "C", "era": "modern", "culture": "american",
                         "seed": 5, "sizeBlocks": [3, 3]}, tmp_path, handoff=True)
    assert paths["instancing"].exists()
    assert m["roles"]["CityInstancing"] == paths["instancing"].name
    assert paths["instancing"].name in m["files"]
    hand = json.loads(paths["handoff"].read_text())
    assert any(r["role"] == "CityInstancing" for r in hand["roles"])


def test_deterministic(tmp_path):
    a, pa = generate({"name": "C", "era": "modern", "culture": "american", "seed": 5}, tmp_path / "a")
    b, pb = generate({"name": "C", "era": "modern", "culture": "american", "seed": 5}, tmp_path / "b")
    assert pa["instancing"].read_bytes() == pb["instancing"].read_bytes()

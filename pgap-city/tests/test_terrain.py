"""Terrain hook (FR7) + landmark slots (FR4)."""

import json

from psc.pipeline import generate
from psc.spec import validate_spec


def _gen(tmp_path, **over):
    spec = {"name": "T", "era": "modern", "culture": "american", "seed": 5,
            "sizeBlocks": [3, 3], **over}
    manifest, paths = generate(spec, tmp_path)
    return manifest, json.loads(paths["layout"].read_text())


def test_no_terrain_keeps_ground_at_zero(tmp_path):
    _, lay = _gen(tmp_path)
    assert all(i["z"] == 0.0 for i in lay["instances"])
    assert "terrain" not in lay


def test_flat_terrain_sits_at_sea_level(tmp_path):
    _, lay = _gen(tmp_path, terrain={"seaLevelM": 10.0})
    assert all(abs(i["z"] - 1000.0) < 1e-6 for i in lay["instances"])   # 10 m -> 1000 cm
    assert lay["terrain"]["seaLevelM"] == 10.0


def test_height_grid_lifts_the_centre(tmp_path):
    _, lay = _gen(tmp_path, terrain={"seaLevelM": 0.0, "extentM": [400, 400],
                                     "heightGrid": [[0, 0, 0], [0, 20, 0], [0, 0, 0]]})
    ext = lay["extentM"]
    zc = [(abs(i["x"] / 100 - ext[0] / 2) + abs(i["y"] / 100 - ext[1] / 2), i["z"])
          for i in lay["instances"]]
    zc.sort()
    assert zc[0][1] > zc[-1][1]                          # centre sits higher than edge


def test_origin_offsets_the_city(tmp_path):
    _, base = _gen(tmp_path / "a")
    _, off = _gen(tmp_path / "b", terrain={"seaLevelM": 0.0, "originM": [500, 0]})
    assert off["instances"][0]["x"] == base["instances"][0]["x"] + 50000.0   # +500 m


def test_landmarks_are_flagged_and_tall(tmp_path):
    man, lay = _gen(tmp_path, landmarks=["CityHall", "GrandSpire"])
    assert man["counts"]["landmarks"] == 2
    flagged = [i for i in lay["instances"] if i.get("landmark")]
    assert len(flagged) == 2
    tallest_normal = max(i["height_m"] for i in lay["instances"] if not i.get("landmark"))
    assert all(i["height_m"] >= tallest_normal for i in flagged)            # hero towers
    assert {l["name"] for l in lay["landmarks"]} == {"CityHall", "GrandSpire"}


def test_spec_validates_terrain_and_landmarks():
    v = validate_spec({"era": "modern", "culture": "american",
                       "landmarks": ["a", 3, "b"], "terrain": {"seaLevelM": 5, "junk": 1}})
    assert v["ok"]
    assert v["normalized"]["landmarks"] == ["a", "b"]                       # non-str dropped
    assert v["normalized"]["terrain"] == {"seaLevelM": 5.0}                 # unknown keys dropped


def test_terrain_deterministic(tmp_path):
    a, _ = _gen(tmp_path / "a", terrain={"seaLevelM": 8.0}, landmarks=["X"])
    b, _ = _gen(tmp_path / "b", terrain={"seaLevelM": 8.0}, landmarks=["X"])
    assert a["files"] == b["files"]

"""City-plan preview: valid PNG, deterministic, emitted + tracked by the pipeline."""

from __future__ import annotations

import numpy as np

from psc import generate
from psc.network import generate_layout
from psc.render import render_plan
from psc.styles import profile_for

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _layout(seed=5):
    return generate_layout(profile_for("modern", "american"), [4, 4], seed, 0.8)


def test_plan_is_rgb_and_sized():
    img = render_plan(_layout(), size_px=512)
    assert img.shape == (512, 512, 3) and img.dtype == np.uint8


def test_plan_has_streets_and_buildings():
    img = render_plan(_layout())
    colors = {tuple(c) for c in img.reshape(-1, 3)[::101]}
    assert len(colors) > 5          # ground + streets + varied building shades, not flat


def test_plan_deterministic():
    a = render_plan(_layout(7))
    b = render_plan(_layout(7))
    assert np.array_equal(a, b)


def test_pipeline_emits_plan_png(tmp_path):
    m, paths = generate({"name": "City", "era": "modern", "culture": "american",
                         "seed": 5, "sizeBlocks": [3, 3]}, tmp_path)
    assert paths["plan"].exists()
    assert paths["plan"].read_bytes()[:8] == PNG_SIG
    assert paths["plan"].name in m["files"]      # SHA-tracked in the manifest


def test_japan_denser_than_american(tmp_path):
    a, _ = generate({"era": "modern", "culture": "american", "seed": 5, "sizeBlocks": [4, 4]},
                    tmp_path / "a")
    j, _ = generate({"era": "modern", "culture": "japan", "seed": 5, "sizeBlocks": [4, 4]},
                    tmp_path / "j")
    assert j["counts"]["instances"] > a["counts"]["instances"]

"""Per-style street networks (FR3): grid / fine_grid / organic / curved_industrial."""

from psc import network
from psc.styles import profile_for


def _layout(cell, seed=7, size=(4, 4)):
    return network.generate_layout(profile_for(*cell), list(size), seed,
                                   profile_for(*cell)["density"])


def test_grid_blocks_are_uniform():
    lay = _layout(("modern", "american"))
    base = lay["blockSizeM"]
    assert all(abs(b["w_m"] - base) < 1e-6 and abs(b["d_m"] - base) < 1e-6 for b in lay["blocks"])
    assert lay["streetNet"] == "grid"


def test_organic_jitters_block_sizes():
    lay = _layout(("futuristic", "cyberpunk"))
    widths = {round(b["w_m"], 1) for b in lay["blocks"]}
    assert len(widths) > 1                       # not a uniform grid
    assert lay["streetNet"] == "organic"


def test_cyberpunk_has_megablock_towers():
    lay = _layout(("futuristic", "cyberpunk"))
    base = lay["blockSizeM"]
    # a megablock building fills most of a block (much bigger than a subdivided lot)
    assert max(i["footprint_m"][0] for i in lay["instances"]) > base * 0.6


def test_japan_is_denser_than_american():
    jp = _layout(("modern", "japan"))
    am = _layout(("modern", "american"))
    assert jp["counts"]["instances"] > am["counts"]["instances"]
    assert jp["blockSizeM"] < am["blockSizeM"]   # fine grid = smaller blocks


def test_extent_recorded_and_streets_span_it():
    lay = _layout(("futuristic", "steampunk"))
    ex, ey = lay["extentM"]
    assert ex > 0 and ey > 0
    for st in lay["streets"]:                    # streets span the full extent
        if st["axis"] == "v":
            assert st["to_m"] == ey
        else:
            assert st["to_m"] == ex


def test_networks_deterministic():
    a = _layout(("futuristic", "cyberpunk"))
    b = _layout(("futuristic", "cyberpunk"))
    assert a["instances"] == b["instances"] and a["streets"] == b["streets"]

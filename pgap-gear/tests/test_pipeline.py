"""Pipeline: spec validation, materials, the output bundle, determinism, handoff."""

import json

from pgear.materials import resolve_materials
from pgear.pipeline import generate
from pgear.registry import TEMPLATES
from pgear.spec import validate_spec


def test_unknown_template_fails_closed():
    assert not validate_spec({"template": "lightsaber"})["ok"]


def test_bad_variant_warns_and_defaults():
    v = validate_spec({"template": "sword", "variant": "chainsaw"})
    assert v["ok"] and v["warnings"]
    assert v["normalized"]["variant"] == "straight"


def test_material_keywords_resolve_slots():
    m = resolve_materials("a curved obsidian blade with a gold guard", "steel", "leather", "bronze")
    assert m["metal"] == "obsidian" and m["accent"] == "gold"
    m = resolve_materials("black steel claws with black leather wraps and glintstone", "steel", "leather", "bronze")
    assert m["metal"] == "dark_steel" and m["grip"] == "leather_black"
    assert m["accent"] == "crystal"
    assert resolve_materials("", "steel", "leather", "bronze")["metal"] == "steel"  # default


def test_generate_emits_full_bundle(tmp_path):
    manifest, paths = generate({"template": "sword", "variant": "curved",
                                "material": "iron", "seed": 5}, tmp_path, handoff=True)
    for key in ("mesh", "preview", "import", "manifest", "handoff"):
        assert paths[key].exists(), key
    sidecar = json.loads(paths["import"].read_text())
    assert sidecar["category"] == "weapon" and sidecar["upAxis"] == "Y"
    assert "grip" in sidecar["sockets"] and sidecar["triangles"] > 0
    assert set(manifest["roles"]) >= {"GearImport", "GearPreview"}
    assert any(r.startswith("GearMesh:") for r in manifest["roles"])


def test_all_templates_generate(tmp_path):
    for name in TEMPLATES:
        manifest, paths = generate({"template": name, "seed": 1}, tmp_path / name)
        assert manifest["counts"]["triangles"] > 0
        g = json.loads(paths["mesh"].read_text())
        assert g["materials"] and g["meshes"][0]["primitives"]


def test_deterministic(tmp_path):
    a, _ = generate({"template": "axe", "material": "bronze wood", "seed": 7}, tmp_path / "a")
    b, _ = generate({"template": "axe", "material": "bronze wood", "seed": 7}, tmp_path / "b")
    assert a["files"] == b["files"]                          # byte-identical SHAs


def test_size_scales_the_mesh(tmp_path):
    import numpy as np
    from pgear.pipeline import build_mesh
    small = build_mesh(validate_spec({"template": "sword", "size": "small"})["normalized"])[0]
    huge = build_mesh(validate_spec({"template": "sword", "size": "huge"})["normalized"])[0]
    assert np.ptp(huge[:, 1]) > np.ptp(small[:, 1]) * 1.5   # huge is taller

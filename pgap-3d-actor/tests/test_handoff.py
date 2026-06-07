"""M5: the source-handoff bundle matches the unreal-mcp-rx contract."""

from __future__ import annotations

import json
from pathlib import Path

from pgap.assemble import assemble_anim_gltf
from pgap.handoff import TAIL_MOTION_BONE, export_source_bundle
from pgap.pipeline import build_bundle
from pgap.rng import make_rng
from pgap.spec import Spec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _export(tmp: Path) -> dict:
    return export_source_bundle(Spec.load(FIXTURE), tmp)


def test_bundle_files_named_by_role(tmp_path):
    r = _export(tmp_path)
    assert Path(r["mesh"]).name == "SK_GoldenRetriever.gltf"
    assert Path(r["animation"]).name == "A_GoldenRetriever_TailWiggle.gltf"
    assert Path(r["texture"]).name == "T_GoldenRetriever_Fur_BaseColor.png"
    for p in (r["mesh"], r["animation"], r["texture"], r["manifest"]):
        assert Path(p).is_file()


def test_manifest_schema_and_metadata(tmp_path):
    r = _export(tmp_path)
    m = json.loads(Path(r["manifest"]).read_text())
    assert m["schemaVersion"] == "game.interactive_component_agent_source_manifest.v1"
    assert m["handoffMode"] == "skeletal_mesh_with_animation"
    roles = {f["roleId"]: f for f in m["files"]}
    assert {"dog_mesh", "tail_animation"} <= set(roles)
    # mesh: create_from_fbx skeleton policy
    assert roles["dog_mesh"]["importCompatibility"]["providedMetadata"]["skeletonPolicy"] == "create_from_fbx"
    # animation: targets the skeleton and the tail_03 motion bone
    anim_meta = roles["tail_animation"]["importCompatibility"]["providedMetadata"]
    assert anim_meta["tailBoneOrSocket"] == TAIL_MOTION_BONE == "tail_03"
    assert anim_meta["targetSkeleton"].endswith("SK_GoldenRetriever_Skeleton")


def test_manifest_sha1_matches_files(tmp_path):
    import hashlib
    r = _export(tmp_path)
    m = json.loads(Path(r["manifest"]).read_text())
    for f in m["files"]:
        data = Path(f["sourceFile"]).read_bytes()
        assert f["sha1"] == hashlib.sha1(data).hexdigest()


def test_anim_gltf_has_skeleton_and_animation_no_mesh(tmp_path):
    r = _export(tmp_path)
    d = json.loads(Path(r["animation"]).read_text())
    assert d.get("animations"), "animation glTF must contain animations"
    assert "meshes" not in d and "skins" not in d, "tail anim glTF must be mesh-less"
    assert len(d["nodes"]) >= 23  # full joint hierarchy present
    # the tail tip bone is animated
    targeted = {d["nodes"][c["target"]["node"]]["name"] for a in d["animations"] for c in a["channels"]}
    assert "tail_03" in targeted


def test_bundle_deterministic(tmp_path):
    a = _export(tmp_path / "a")
    b = _export(tmp_path / "b")
    assert a["files"] == b["files"]  # identical per-role sha1s

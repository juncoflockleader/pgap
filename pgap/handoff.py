"""Source-handoff bundle export (M5).

Emits the role-named source files + a manifest matching the unreal-mcp-rx
source-worker contract (``game.interactive_component_agent_source_manifest.v1``),
so the project-clone proof lane can import the mesh, bind the tail animation,
author the fur material, assemble the Blueprint, and PIE-prove bark + tail-wag.

pgap owns the importable sources (mesh, tail animation, base-color texture). The
bark **audio** is a separate role the lane placeholders — not pgap's scope.

Bridge-independent: this writes files + JSON deterministically. The live lane run
(import/material/assembly/PIE) happens through the MCP tools. The manifest is
authored to the documented v1 schema; reconcile against the tool's emitted
template on first live run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .assemble import assemble_anim_gltf, assemble_gltf
from .pipeline import build_bundle
from .rng import make_rng
from .spec import Spec

_MANIFEST_SCHEMA = "game.interactive_component_agent_source_manifest.v1"
_IMPORT_COMPAT_SCHEMA = "game.interactive_component_source_import_compatibility.v1"
TAIL_MOTION_BONE = "tail_03"  # tip of the tail chain; the wag's most visible bone


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _tail_clip(clips: list):
    for c in clips:
        if c.name == "tail_wag":
            return c
    return clips[0] if clips else None


def _mesh_compat() -> dict:
    return {
        "schemaVersion": _IMPORT_COMPAT_SCHEMA,
        "status": "ready",
        "assetType": "mesh",
        "desiredUnrealAssetType": "skeletal_mesh",
        "sourceFormat": "gltf",
        "importFactory": "skeletal_mesh",
        "requiredMetadata": ["skeleton_policy"],
        "providedMetadata": {"skeletonPolicy": "create_from_fbx"},
        "importOptions": {"factory": "skeletal_mesh", "sourceFormat": "gltf", "skeleton_policy": "create_from_fbx"},
        "missingMetadata": [],
        "acceptance": [
            "source file imports with the planned import factory",
            "post-import inspect confirms the expected Unreal asset type",
            "skeletal mesh import records whether it creates a skeleton or binds to a target skeleton",
            "post-import inspect confirms a skeletal mesh component can bind to the asset",
        ],
    }


def _anim_compat(skeleton_pkg: str) -> dict:
    return {
        "schemaVersion": _IMPORT_COMPAT_SCHEMA,
        "status": "ready",
        "assetType": "animation",
        "desiredUnrealAssetType": "animation_sequence",
        "sourceFormat": "gltf",
        "importFactory": "animation_sequence",
        "requiredMetadata": ["target_skeleton", "tail_bone_or_socket"],
        "providedMetadata": {"targetSkeleton": skeleton_pkg, "tailBoneOrSocket": TAIL_MOTION_BONE},
        "importOptions": {"factory": "animation_sequence", "sourceFormat": "gltf",
                          "target_skeleton": skeleton_pkg, "tail_bone_or_socket": TAIL_MOTION_BONE},
        "missingMetadata": [],
        "acceptance": [
            "source file imports with the planned import factory",
            "post-import inspect confirms the expected Unreal asset type",
            "animation import targets a recorded skeleton",
            "tail motion binding records the animated tail bone or socket",
        ],
    }


def export_source_bundle(
    spec: Spec,
    out_dir: str | Path,
    package_root: str = "/Game/Prototype/Dogs",
    component_id: str = "golden_retriever_interaction",
) -> dict:
    """Write the SK/A/T role files + v1 source manifest. Returns paths + shas."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = spec.name

    rng = make_rng(spec.seed)
    skel, mesh, clips, textures = build_bundle(spec, rng)

    # Role files.
    sk_bytes = assemble_gltf(mesh, name, skel, anims=None, textures=textures)  # mesh+skin+material, no clips
    sk_file = out / f"SK_{name}.gltf"
    sk_file.write_bytes(sk_bytes)

    tail = _tail_clip(clips)
    anim_bytes = assemble_anim_gltf(f"{name}_TailWiggle", skel, [tail] if tail else [])
    anim_file = out / f"A_{name}_TailWiggle.gltf"
    anim_file.write_bytes(anim_bytes)

    tex_bytes = textures["baseColor"]
    tex_file = out / f"T_{name}_Fur_BaseColor.png"
    tex_file.write_bytes(tex_bytes)

    meshes_pkg = f"{package_root}/Meshes/SK_{name}"
    skeleton_pkg = f"{meshes_pkg}_Skeleton"
    anim_pkg = f"{package_root}/Animations/A_{name}_TailWiggle"
    tex_pkg = f"{package_root}/Textures/T_{name}_Fur_BaseColor"

    files = [
        {
            "requestId": f"task_{component_id}.dog_mesh",
            "roleId": "dog_mesh", "role": "dog_mesh",
            "assetType": "mesh", "desiredUnrealAssetType": "skeletal_mesh",
            "targetPackage": meshes_pkg,
            "sourceFile": str(sk_file), "sourceFormat": "gltf",
            "sha1": _sha1(sk_bytes),
            "generator": "pgap-procedural-gltf-generator",
            "prompt": "procedurally generated rigged golden retriever skeletal mesh, Unreal scale, visible tail",
            "licenseNote": "procedurally generated original work",
            "replacementCriteria": ["recognizable golden retriever; correct scale; skeleton compatibility; runtime visual proof"],
            "importCompatibility": _mesh_compat(),
        },
        {
            "requestId": f"task_{component_id}.tail_animation",
            "roleId": "tail_animation", "role": "tail_animation",
            "assetType": "animation", "desiredUnrealAssetType": "animation_sequence",
            "targetPackage": anim_pkg,
            "sourceFile": str(anim_file), "sourceFormat": "gltf",
            "sha1": _sha1(anim_bytes),
            "generator": "pgap-procedural-gltf-generator",
            "prompt": "short looping tail-wag animation on the golden retriever skeleton (bone tail_03)",
            "licenseNote": "procedurally generated original work",
            "replacementCriteria": ["target skeleton compatibility; runtime tail-wiggle PIE evidence"],
            "importCompatibility": _anim_compat(skeleton_pkg),
        },
        {
            "requestId": f"task_{component_id}.fur_texture",
            "roleId": "fur_texture", "role": "fur_texture",
            "assetType": "texture", "desiredUnrealAssetType": "texture",
            "targetPackage": tex_pkg,
            "sourceFile": str(tex_file), "sourceFormat": "png",
            "sha1": _sha1(tex_bytes),
            "generator": "pgap-procedural-gltf-generator",
            "prompt": "golden fur base-color texture",
            "licenseNote": "procedurally generated original work",
            "replacementCriteria": ["golden fur reads correctly on the mesh material"],
        },
    ]

    manifest = {
        "schemaVersion": _MANIFEST_SCHEMA,
        "componentId": component_id,
        "templateId": component_id,
        "handoffMode": "skeletal_mesh_with_animation",
        "sourceFileRoot": str(out),
        "files": files,
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_file = out / f"{name}.source_manifest.json"
    manifest_file.write_bytes(manifest_bytes)

    return {
        "mesh": str(sk_file),
        "animation": str(anim_file),
        "texture": str(tex_file),
        "manifest": str(manifest_file),
        "skeletonPackage": skeleton_pkg,
        "tailMotionBone": TAIL_MOTION_BONE,
        "files": {f["roleId"]: f["sha1"] for f in files},
    }

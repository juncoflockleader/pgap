"""glTF assembler + manifest + import sidecar (DESIGN §3 assembler).

M1: emits a **skinned** glTF (POSITION/NORMAL/JOINTS_0/WEIGHTS_0/indices + skin
with a joint node hierarchy and inverseBindMatrices) when a skeleton is supplied
and the mesh carries weights; otherwise falls back to the M0 static-mesh path.
Also writes the ``<Name>.import.json`` sidecar (target skeleton, tail bone, bone
order) and a provenance ``manifest.json``.

Determinism: the buffer is exact little-endian bytes (u32/f32/u16); node
translations and inverse-bind matrices are plain floats in sorted-key JSON.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import numpy as np

from . import __version__
from .spec import Spec
from .types import Bone, Mesh

# glTF component / accessor constants
_U16 = 5123
_U32 = 5125
_F32 = 5126
_ARRAY_BUFFER = 34962
_ELEMENT_ARRAY_BUFFER = 34963


def _pad4(data: bytes) -> bytes:
    return data + b"\x00" * ((-len(data)) % 4)


class _BufferBuilder:
    """Accumulates byte sections, each 4-byte aligned, tracking offsets."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._cursor = 0

    def add(self, raw: bytes) -> tuple[int, int]:
        offset = self._cursor
        padded = _pad4(raw)
        self._chunks.append(padded)
        self._cursor += len(padded)
        return offset, len(raw)

    def bytes(self) -> bytes:
        return b"".join(self._chunks)


def _ibm_columns(head: np.ndarray) -> list[float]:
    """Column-major inverse bind matrix = translate(-head); rest = identity."""
    hx, hy, hz = float(head[0]), float(head[1]), float(head[2])
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        -hx, -hy, -hz, 1.0,
    ]


def assemble_gltf(
    mesh: Mesh,
    name: str,
    skel: list[Bone] | None = None,
    anims: list | None = None,
    textures: dict | None = None,
) -> bytes:
    """Build a glTF 2.0 document (skinned + animated + textured if inputs present)."""
    skinned = skel is not None and mesh.joints is not None and mesh.weights is not None

    positions = np.ascontiguousarray(mesh.positions, dtype="<f4")
    normals = np.ascontiguousarray(mesh.normals, dtype="<f4")
    indices = np.ascontiguousarray(mesh.indices, dtype="<u4")
    pos_min = positions.reshape(-1, 3).min(axis=0).astype(float).tolist()
    pos_max = positions.reshape(-1, 3).max(axis=0).astype(float).tolist()

    buf = _BufferBuilder()
    buffer_views: list[dict] = []
    accessors: list[dict] = []

    def add_view(raw, target=None):
        off, length = buf.add(raw)
        bv = {"buffer": 0, "byteOffset": off, "byteLength": length}
        if target is not None:
            bv["target"] = target
        buffer_views.append(bv)
        return len(buffer_views) - 1

    def add_accessor(raw, component_type, count, atype, lo=None, hi=None, target=None):
        bv = add_view(raw, target)
        acc = {"bufferView": bv, "componentType": component_type, "count": count, "type": atype}
        if lo is not None:
            acc["min"] = lo
        if hi is not None:
            acc["max"] = hi
        accessors.append(acc)
        return len(accessors) - 1

    # Core geometry attributes.
    idx_acc = add_accessor(indices.tobytes(), _U32, int(indices.shape[0]), "SCALAR", target=_ELEMENT_ARRAY_BUFFER)
    attributes = {
        "POSITION": add_accessor(positions.tobytes(), _F32, int(positions.shape[0]), "VEC3", lo=pos_min, hi=pos_max, target=_ARRAY_BUFFER),
        "NORMAL": add_accessor(normals.tobytes(), _F32, int(normals.shape[0]), "VEC3", target=_ARRAY_BUFFER),
    }
    if mesh.uvs is not None:
        uvs = np.ascontiguousarray(mesh.uvs, dtype="<f4")
        attributes["TEXCOORD_0"] = add_accessor(uvs.tobytes(), _F32, int(uvs.shape[0]), "VEC2", target=_ARRAY_BUFFER)
    if mesh.colors is not None:
        cols = np.ascontiguousarray(mesh.colors, dtype="<f4")
        attributes["COLOR_0"] = add_accessor(cols.tobytes(), _F32, int(cols.shape[0]), "VEC4", target=_ARRAY_BUFFER)

    if skinned:
        joints = np.ascontiguousarray(mesh.joints, dtype="<u2")
        weights = np.ascontiguousarray(mesh.weights, dtype="<f4")
        attributes["JOINTS_0"] = add_accessor(joints.tobytes(), _U16, int(joints.shape[0]), "VEC4", target=_ARRAY_BUFFER)
        attributes["WEIGHTS_0"] = add_accessor(weights.tobytes(), _F32, int(weights.shape[0]), "VEC4", target=_ARRAY_BUFFER)
        ibm = np.array([_ibm_columns(b.head) for b in skel], dtype="<f4").reshape(-1)
        ibm_acc = add_accessor(ibm.tobytes(), _F32, len(skel), "MAT4")

    primitive = {"attributes": attributes, "indices": idx_acc, "mode": 4}

    doc: dict = {
        "asset": {"version": "2.0", "generator": f"pgap {__version__}"},
        "scene": 0,
    }

    # Material + embedded base-color texture.
    if textures and textures.get("baseColor"):
        img_bv = add_view(textures["baseColor"])
        doc["images"] = [{"bufferView": img_bv, "mimeType": "image/png"}]
        doc["samplers"] = [{"wrapS": 10497, "wrapT": 10497}]  # REPEAT
        doc["textures"] = [{"source": 0, "sampler": 0}]
        doc["materials"] = [{
            "name": f"{name}_Mat",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "baseColorTexture": {"index": 0, "texCoord": 0},
                "metallicFactor": float(textures.get("metallicFactor", 0.0)),
                "roughnessFactor": float(textures.get("roughnessFactor", 0.9)),
            },
            "doubleSided": True,
        }]
        # Optional surface normal map (scales/feathers/fur/chitin/bark relief).
        if textures.get("normal"):
            nrm_bv = add_view(textures["normal"])
            doc["images"].append({"bufferView": nrm_bv, "mimeType": "image/png"})
            doc["textures"].append({"source": len(doc["images"]) - 1, "sampler": 0})
            doc["materials"][0]["normalTexture"] = {
                "index": len(doc["textures"]) - 1, "texCoord": 0,
            }
        primitive["material"] = 0

    doc["meshes"] = [{"name": name, "primitives": [primitive]}]

    if skinned:
        name_to_idx = {b.name: i for i, b in enumerate(skel)}
        head_of = {b.name: b.head for b in skel}
        children: dict[int, list[int]] = {i: [] for i in range(len(skel))}
        for i, b in enumerate(skel):
            if b.parent is not None and b.parent in name_to_idx:
                children[name_to_idx[b.parent]].append(i)

        nodes = []
        for i, b in enumerate(skel):
            if b.parent is not None and b.parent in head_of:
                local = np.asarray(b.head) - np.asarray(head_of[b.parent])
            else:
                local = np.asarray(b.head)
            node = {"name": b.name, "translation": [float(x) for x in local]}
            if children[i]:
                node["children"] = children[i]
            nodes.append(node)

        mesh_node_idx = len(skel)
        nodes.append({"name": name, "mesh": 0, "skin": 0})
        doc["nodes"] = nodes
        doc["scenes"] = [{"nodes": [0, mesh_node_idx]}]
        doc["skins"] = [{"joints": list(range(len(skel))), "inverseBindMatrices": ibm_acc, "skeleton": 0}]

        if anims:
            animations_doc = []
            for clip in anims:
                times = np.ascontiguousarray(clip.times, dtype="<f4")
                if times.size == 0 or not clip.channels:
                    continue
                t_acc = add_accessor(
                    times.tobytes(), _F32, int(times.shape[0]), "SCALAR",
                    lo=[float(times.min())], hi=[float(times.max())],
                )
                samplers, channels = [], []
                for ch in clip.channels:
                    node = name_to_idx.get(ch.bone)
                    if node is None:
                        continue
                    vals = np.ascontiguousarray(ch.values, dtype="<f4")
                    atype = "VEC4" if ch.path == "rotation" else "VEC3"
                    v_acc = add_accessor(vals.tobytes(), _F32, int(vals.shape[0]), atype)
                    samplers.append({"input": t_acc, "output": v_acc, "interpolation": "LINEAR"})
                    channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": ch.path}})
                if channels:
                    animations_doc.append({"name": clip.name, "samplers": samplers, "channels": channels})
            if animations_doc:
                doc["animations"] = animations_doc
    else:
        doc["nodes"] = [{"mesh": 0, "name": name}]
        doc["scenes"] = [{"nodes": [0]}]

    buffer = buf.bytes()
    uri = "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ascii")
    doc["buffers"] = [{"byteLength": len(buffer), "uri": uri}]
    doc["bufferViews"] = buffer_views
    doc["accessors"] = accessors

    return json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8")


def assemble_anim_gltf(name: str, skel: list[Bone], clips: list) -> bytes:
    """Animation-only glTF: the joint-node skeleton + animation channels, no mesh.

    For the M5 source-handoff `A_<Name>_TailWiggle.gltf` role — imports as an
    AnimSequence binding to the skeleton created from the mesh (matching bone
    names). Same joint hierarchy/local-translation convention as the skinned mesh
    so rotations rotate about each joint's head.
    """
    buf = _BufferBuilder()
    buffer_views: list[dict] = []
    accessors: list[dict] = []

    def add_accessor(raw, component_type, count, atype, lo=None, hi=None):
        off, length = buf.add(raw)
        buffer_views.append({"buffer": 0, "byteOffset": off, "byteLength": length})
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": component_type,
                          "count": count, "type": atype, **({"min": lo} if lo else {}), **({"max": hi} if hi else {})})
        return len(accessors) - 1

    name_to_idx = {b.name: i for i, b in enumerate(skel)}
    head_of = {b.name: b.head for b in skel}
    children: dict[int, list[int]] = {i: [] for i in range(len(skel))}
    for i, b in enumerate(skel):
        if b.parent is not None and b.parent in name_to_idx:
            children[name_to_idx[b.parent]].append(i)
    nodes = []
    for i, b in enumerate(skel):
        local = (np.asarray(b.head) - np.asarray(head_of[b.parent])) if (b.parent in head_of) else np.asarray(b.head)
        node = {"name": b.name, "translation": [float(x) for x in local]}
        if children[i]:
            node["children"] = children[i]
        nodes.append(node)

    animations_doc = []
    for clip in clips:
        times = np.ascontiguousarray(clip.times, dtype="<f4")
        if times.size == 0 or not clip.channels:
            continue
        t_acc = add_accessor(times.tobytes(), _F32, int(times.shape[0]), "SCALAR",
                             lo=[float(times.min())], hi=[float(times.max())])
        samplers, channels = [], []
        for ch in clip.channels:
            node = name_to_idx.get(ch.bone)
            if node is None:
                continue
            vals = np.ascontiguousarray(ch.values, dtype="<f4")
            atype = "VEC4" if ch.path == "rotation" else "VEC3"
            v_acc = add_accessor(vals.tobytes(), _F32, int(vals.shape[0]), atype)
            samplers.append({"input": t_acc, "output": v_acc, "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": ch.path}})
        if channels:
            animations_doc.append({"name": clip.name, "samplers": samplers, "channels": channels})

    buffer = buf.bytes()
    uri = "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ascii")
    doc = {
        "asset": {"version": "2.0", "generator": f"pgap {__version__}"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
        "animations": animations_doc,
        "buffers": [{"byteLength": len(buffer), "uri": uri}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    return json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _spec_hash(spec: Spec) -> str:
    canonical = json.dumps(
        {
            "archetype": spec.archetype,
            "species": spec.species,
            "seed": spec.seed,
            "triBudget": spec.tri_budget,
            "name": spec.name,
            "proportions": spec.proportions,
            "traits": spec.traits,
            "material": spec.material,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha1(canonical.encode("utf-8"))


def _import_sidecar_bytes(spec: Spec, skel: list[Bone], anims: list | None) -> bytes:
    sidecar = {
        "archetype": spec.archetype,
        "targetSkeletonName": spec.target_skeleton,
        "tailBone": spec.tail_bone,
        "skeletonPolicy": "useGenerated",
        "bones": [b.name for b in skel],
        "animations": [c.name for c in (anims or [])],
    }
    return json.dumps(sidecar, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_outputs(
    mesh: Mesh,
    spec: Spec,
    out_dir: str | Path,
    skel: list[Bone] | None = None,
    anims: list | None = None,
    textures: dict | None = None,
) -> dict:
    """Write glTF (+ textures + import.json if skinned) + manifest; return paths/SHAs."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    gltf_bytes = assemble_gltf(mesh, spec.name, skel, anims, textures)
    gltf_path = out / f"{spec.name}.gltf"
    gltf_path.write_bytes(gltf_bytes)
    files = {gltf_path.name: _sha1(gltf_bytes)}
    result = {"gltf": str(gltf_path), "gltf_sha1": files[gltf_path.name]}

    if textures and textures.get("baseColor"):
        png_path = out / f"{spec.name}_BaseColor.png"
        png_path.write_bytes(textures["baseColor"])
        files[png_path.name] = _sha1(textures["baseColor"])
        result["baseColor"] = str(png_path)

    if textures and textures.get("normal"):
        nrm_path = out / f"{spec.name}_Normal.png"
        nrm_path.write_bytes(textures["normal"])
        files[nrm_path.name] = _sha1(textures["normal"])
        result["normal"] = str(nrm_path)

    if skel is not None:
        sidecar_bytes = _import_sidecar_bytes(spec, skel, anims)
        sidecar_path = out / f"{spec.name}.import.json"
        sidecar_path.write_bytes(sidecar_bytes)
        files[sidecar_path.name] = _sha1(sidecar_bytes)
        result["import"] = str(sidecar_path)

    manifest = {
        "generator": "pgap",
        "generatorVersion": __version__,
        "specHash": _spec_hash(spec),
        "seed": spec.seed,
        "files": files,
        "license": "procedurally generated original work",
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_path = out / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    result["manifest"] = str(manifest_path)
    return result

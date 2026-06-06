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
) -> bytes:
    """Build a glTF 2.0 document (skinned + animated if inputs present)."""
    skinned = skel is not None and mesh.joints is not None and mesh.weights is not None

    positions = np.ascontiguousarray(mesh.positions, dtype="<f4")
    normals = np.ascontiguousarray(mesh.normals, dtype="<f4")
    indices = np.ascontiguousarray(mesh.indices, dtype="<u4")

    buf = _BufferBuilder()
    idx_off, idx_len = buf.add(indices.tobytes())
    pos_off, pos_len = buf.add(positions.tobytes())
    nrm_off, nrm_len = buf.add(normals.tobytes())

    pos_min = positions.reshape(-1, 3).min(axis=0).astype(float).tolist()
    pos_max = positions.reshape(-1, 3).max(axis=0).astype(float).tolist()

    buffer_views = [
        {"buffer": 0, "byteOffset": idx_off, "byteLength": idx_len, "target": _ELEMENT_ARRAY_BUFFER},
        {"buffer": 0, "byteOffset": pos_off, "byteLength": pos_len, "target": _ARRAY_BUFFER},
        {"buffer": 0, "byteOffset": nrm_off, "byteLength": nrm_len, "target": _ARRAY_BUFFER},
    ]
    accessors = [
        {"bufferView": 0, "componentType": _U32, "count": int(indices.shape[0]), "type": "SCALAR"},
        {"bufferView": 1, "componentType": _F32, "count": int(positions.shape[0]), "type": "VEC3", "min": pos_min, "max": pos_max},
        {"bufferView": 2, "componentType": _F32, "count": int(normals.shape[0]), "type": "VEC3"},
    ]
    attributes = {"POSITION": 1, "NORMAL": 2}

    def add_accessor(raw, component_type, count, atype, lo=None, hi=None):
        off, length = buf.add(raw)
        buffer_views.append({"buffer": 0, "byteOffset": off, "byteLength": length})
        acc = {"bufferView": len(buffer_views) - 1, "componentType": component_type,
               "count": count, "type": atype}
        if lo is not None:
            acc["min"] = lo
        if hi is not None:
            acc["max"] = hi
        accessors.append(acc)
        return len(accessors) - 1

    doc: dict = {
        "asset": {"version": "2.0", "generator": f"pgap {__version__}"},
        "scene": 0,
    }

    if skinned:
        joints = np.ascontiguousarray(mesh.joints, dtype="<u2")
        weights = np.ascontiguousarray(mesh.weights, dtype="<f4")
        ibm = np.array(
            [_ibm_columns(b.head) for b in skel], dtype="<f4"
        ).reshape(-1)

        jnt_off, jnt_len = buf.add(joints.tobytes())
        wgt_off, wgt_len = buf.add(weights.tobytes())
        ibm_off, ibm_len = buf.add(ibm.tobytes())

        buffer_views += [
            {"buffer": 0, "byteOffset": jnt_off, "byteLength": jnt_len, "target": _ARRAY_BUFFER},
            {"buffer": 0, "byteOffset": wgt_off, "byteLength": wgt_len, "target": _ARRAY_BUFFER},
            {"buffer": 0, "byteOffset": ibm_off, "byteLength": ibm_len},
        ]
        accessors += [
            {"bufferView": 3, "componentType": _U16, "count": int(joints.shape[0]), "type": "VEC4"},
            {"bufferView": 4, "componentType": _F32, "count": int(weights.shape[0]), "type": "VEC4"},
            {"bufferView": 5, "componentType": _F32, "count": len(skel), "type": "MAT4"},
        ]
        attributes["JOINTS_0"] = 3
        attributes["WEIGHTS_0"] = 4

        # Joint nodes (indices 0..B-1), hierarchy via local translations.
        name_to_idx = {b.name: i for i, b in enumerate(skel)}
        head_of = {b.name: b.head for b in skel}
        children: dict[int, list[int]] = {i: [] for i in range(len(skel))}
        for i, b in enumerate(skel):
            if b.parent is not None and b.parent in name_to_idx:
                children[name_to_idx[b.parent]].append(i)

        nodes = []
        for i, b in enumerate(skel):
            if b.parent is not None and b.parent in head_of:
                local = (np.asarray(b.head) - np.asarray(head_of[b.parent]))
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
        doc["skins"] = [{"joints": list(range(len(skel))), "inverseBindMatrices": 5, "skeleton": 0}]
        doc["meshes"] = [{"name": name, "primitives": [{"attributes": attributes, "indices": 0, "mode": 4}]}]

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
        doc["meshes"] = [{"name": name, "primitives": [{"attributes": attributes, "indices": 0, "mode": 4}]}]

    buffer = buf.bytes()
    uri = "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ascii")
    doc["buffers"] = [{"byteLength": len(buffer), "uri": uri}]
    doc["bufferViews"] = buffer_views
    doc["accessors"] = accessors

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
) -> dict:
    """Write glTF (+ import.json if skinned) + manifest; return paths and SHAs."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    gltf_bytes = assemble_gltf(mesh, spec.name, skel, anims)
    gltf_path = out / f"{spec.name}.gltf"
    gltf_path.write_bytes(gltf_bytes)
    files = {gltf_path.name: _sha1(gltf_bytes)}
    result = {"gltf": str(gltf_path), "gltf_sha1": files[gltf_path.name]}

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

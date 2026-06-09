"""Generate gear outputs from a spec: a multi-material static-mesh glTF + a preview
PNG + an import sidecar + a manifest (+ --handoff source bundle). Deterministic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from . import gltf, materials, render
from .geom import MeshBuilder
from .registry import SIZE_SCALE, TEMPLATES
from .spec import validate_spec

GENERATOR_VERSION = "0.1.0"


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _spec_hash(normalized: Dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_mesh(s: Dict[str, Any]):
    """Normalized spec -> (pos, nrm, idx, tri_mat, sockets, material_slots, template)."""
    t = TEMPLATES[s["template"]]
    mats = materials.resolve_materials(s["material"], t["mats"]["metal"],
                                       t["mats"]["grip"], t["mats"]["accent"])
    scale = SIZE_SCALE[s["size"]] * t["scale"]
    mb = MeshBuilder()
    sockets = t["fn"](mb, mats, scale, s["variant"])
    pos, nrm, idx, tri_mat = mb.build()
    return pos, nrm, idx, tri_mat, sockets, mats, t


def generate(spec: Dict[str, Any], out_dir: str | Path, *, handoff: bool = False) -> Tuple[Dict[str, Any], Dict[str, Path]]:
    v = validate_spec(spec)
    if not v["ok"]:
        raise ValueError("invalid gear spec: " + "; ".join(v["errors"]))
    s = v["normalized"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = str(s["name"])
    pos, nrm, idx, tri_mat, sockets, mats, t = build_mesh(s)
    used_materials = sorted(set(tri_mat))
    paths: Dict[str, Path] = {}

    mesh_path = out / f"SM_{name}.gltf"
    mesh_path.write_bytes(gltf.gear_gltf(pos, nrm, idx, tri_mat, name=f"SM_{name}"))
    paths["mesh"] = mesh_path

    preview_path = out / f"{name}_Preview.png"
    preview_path.write_bytes(render.render_png(pos, nrm, idx, tri_mat))
    paths["preview"] = preview_path

    lo, hi = pos.min(0), pos.max(0)
    sidecar = {
        "schemaVersion": "pgear.import.v1",
        "name": name, "category": t["category"], "mesh": mesh_path.name,
        "unit": "m", "upAxis": "Y", "pivot": [0.0, 0.0, 0.0],
        "sockets": {k: {"location": [0.0, round(float(yv), 4), 0.0]} for k, yv in sockets.items()},
        "materials": used_materials,
        "materialSlots": mats,
        "bounds": {"min": [round(float(x), 4) for x in lo],
                   "max": [round(float(x), 4) for x in hi]},
        "triangles": int(len(idx) // 3),
    }
    import_path = out / f"{name}.import.json"
    import_path.write_text(json.dumps(sidecar, indent=2))
    paths["import"] = import_path

    manifest = {
        "schemaVersion": "pgear.manifest.v1",
        "name": name, "generator": "pgear", "generatorVersion": GENERATOR_VERSION,
        "template": s["template"], "variant": s["variant"], "size": s["size"],
        "category": t["category"], "materialSlots": mats, "seed": int(s["seed"]),
        "specHash": _spec_hash(s),
        "license": "procedurally generated original work",
        "files": {p.name: _sha1(p) for p in (mesh_path, preview_path, import_path)},
        "roles": {f"GearMesh:{name}": mesh_path.name, "GearImport": import_path.name,
                  "GearPreview": preview_path.name},
        "counts": {"triangles": int(len(idx) // 3), "materials": len(used_materials)},
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    paths["manifest"] = manifest_path

    if handoff:
        hand = out / "handoff"
        hand.mkdir(exist_ok=True)
        src = {
            "schemaVersion": "game.interactive_component_agent_source_manifest.v1",
            "name": name,
            "roles": [
                {"role": f"GearMesh:{name}", "file": mesh_path.name},
                {"role": "GearImport", "file": import_path.name},
                {"role": "GearPreview", "file": preview_path.name},
            ],
        }
        (hand / "handoff.manifest.json").write_text(json.dumps(src, indent=2))
        paths["handoff"] = hand / "handoff.manifest.json"

    return manifest, paths

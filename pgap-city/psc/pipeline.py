"""Generate city outputs from a spec (C0: layout graph + style spec + manifest).

C1+ adds the building-kit glTF assembly (reusing the pgap-3d-actor module engine),
roads, props meshes, and the full --handoff role set (see PRD.md). C0 emits the
deterministic layout (instance transforms) + the style/material spec + manifest so
the engine round-trip (bulk HISM instancing) can be stood up.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import zlib

import numpy as np

from . import facade, gltf, instancing, network, render
from .pngio import encode_rgb8, write_rgb8
from .render import ZONE_COLOR
from .spec import validate_spec
from .styles import MODULE_KINDS, facade_for, profile_for

GENERATOR_VERSION = "0.2.0"  # C1: skinned building kits (facade + roof textures)


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _spec_hash(normalized: Dict[str, Any]) -> str:
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def generate(spec: Dict[str, Any], out_dir: str | Path, *, handoff: bool = False) -> Tuple[Dict[str, Any], Dict[str, Path]]:
    v = validate_spec(spec)
    if not v["ok"]:
        raise ValueError("invalid city spec: " + "; ".join(v["errors"]))
    s = v["normalized"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = str(s["name"])
    era, culture = s["era"], s["culture"]
    profile = profile_for(era, culture)

    layout = network.generate_layout(profile, s["sizeBlocks"], int(s["seed"]), float(s["density"]))
    layout["name"] = name
    layout["cell"] = f"{era}x{culture}"
    kit_ids = sorted({inst["kit"] for inst in layout["instances"]})

    paths: Dict[str, Path] = {}

    # C1 building kit: one *skinned* box mesh (SM_<kit>.gltf) per variant — a facade
    # texture (wall + window grid + ground floor + parapet) on the sides and a roof
    # texture on top, embedded in the glTF. Instances HISM it with location (x,y,z)
    # cm + yaw + scale3 (m); a few skinned meshes build the whole textured skyline.
    fstyle = facade_for(profile)
    bay_m = float(fstyle["bay_m"])
    texture_paths: list[Path] = []
    kit_meshes: Dict[str, Path] = {}
    kits_meta = []
    for kit in kit_ids:
        zone = kit.rsplit("_", 1)[-1]
        insts = [i for i in layout["instances"] if i["kit"] == kit]
        widths = [float(i["footprint_m"][0]) for i in insts] or [40.0]
        floors = [int(i["floors"]) for i in insts] or [3]
        cols = int(min(8, max(1, round(float(np.median(widths)) / bay_m))))
        rows = int(min(14, max(1, round(float(np.median(floors))))))
        krng = np.random.default_rng((int(s["seed"]) ^ zlib.crc32(kit.encode())) & 0xFFFFFFFF)
        wall_base, wall_nrm, wall_emis = facade.synth_facade(fstyle, cols, rows, krng)
        roof_base, roof_nrm = facade.synth_roof(fstyle, krng)

        # write the skin PNGs (inspection + handoff) and embed them in the kit glTF
        def _png(suffix: str, arr) -> Path:
            p = out / f"SM_{kit}_{suffix}.png"
            write_rgb8(str(p), arr)
            texture_paths.append(p)
            return p
        _png("BaseColor", wall_base)
        _png("Normal", wall_nrm)
        _png("Roof", roof_base)
        if wall_emis is not None:
            _png("Emissive", wall_emis)

        mesh_path = out / f"SM_{kit}.gltf"
        mesh_path.write_bytes(gltf.building_gltf(
            encode_rgb8(wall_base), encode_rgb8(wall_nrm),
            encode_rgb8(roof_base), encode_rgb8(roof_nrm),
            wall_emissive=encode_rgb8(wall_emis) if wall_emis is not None else None,
            roughness=float(profile.get("roughness", 0.8)), name=f"SM_{kit}"))
        kit_meshes[kit] = mesh_path
        paths[f"kit_{kit}"] = mesh_path
        kits_meta.append({"id": kit, "mesh": mesh_path.name, "zone": zone,
                          "baseColor": list(ZONE_COLOR.get(zone, (150, 150, 150))),
                          "facade": {"cols": cols, "rows": rows,
                                     "emissive": wall_emis is not None}})
    layout["kits"] = kits_meta
    layout["instanceModel"] = (
        "SM_<kit>.gltf is a 1 m Y-up box skinned with an embedded facade texture "
        "(walls: base-color + normal, optional emissive) + a roof texture; it imports "
        "upright (base on ground). Per instance: place at (x,y,z) cm, rotate yaw (deg, "
        "about up), scale by scale3 = [width, depth, height] in m. Window scale is the "
        "kit's representative size; per-instance-uniform windows want a UE "
        "world-aligned/triplanar facade material (handoff upgrade).")

    layout_path = out / f"{name}.city.layout.json"
    layout_path.write_text(json.dumps(layout, indent=2))
    paths["layout"] = layout_path

    # top-down plan preview (inspection aid; not an engine role)
    plan_path = out / f"{name}_Plan.png"
    write_rgb8(str(plan_path), render.render_plan(layout))
    paths["plan"] = plan_path

    # per-kit bulk-instancing payloads for unreal-mcp-rx editor_instances_place
    # (import SM_<kit>, set mesh_path, send one HISM call per kit).
    instancing_path = out / f"{name}.instances.json"
    instancing_path.write_text(json.dumps(instancing.instancing_payloads(layout), indent=2))
    paths["instancing"] = instancing_path

    style_spec = {
        "schemaVersion": "psc.style.material.v1",
        "cell": f"{era}x{culture}",
        "materials": profile["materials"],
        "palette": profile["palette"],
        "roof": profile["roof"],
        "props": profile["props"],
        "moduleKinds": list(MODULE_KINDS),
    }
    style_path = out / "StyleMaterialSpec.json"
    style_path.write_text(json.dumps(style_spec, indent=2))
    paths["style"] = style_path

    manifest = {
        "schemaVersion": "psc.manifest.v1",
        "name": name,
        "cell": f"{era}x{culture}",
        "generator": "psc",
        "generatorVersion": GENERATOR_VERSION,
        "seed": int(s["seed"]),
        "specHash": _spec_hash(s),
        "license": "procedurally generated original work",
        "files": {p.name: _sha1(p) for p in
                  (layout_path, style_path, plan_path, instancing_path,
                   *kit_meshes.values(), *texture_paths)},
        "roles": {
            "CityLayout": layout_path.name,
            "StyleMaterialSpec": style_path.name,
            "CityInstancing": instancing_path.name,
            **{f"BuildingKit:{kit}": kit_meshes[kit].name for kit in kit_ids},
        },
        "counts": {**layout["counts"], "kits": len(kit_ids)},
        "pending": ["RoadNetwork", "PropScatter"],
        "warnings": v["warnings"],
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
                {"role": "CityLayout", "file": layout_path.name},
                {"role": "StyleMaterialSpec", "file": style_path.name},
                {"role": "CityInstancing", "file": instancing_path.name},
                *[{"role": f"BuildingKit:{kit}", "file": kit_meshes[kit].name} for kit in kit_ids],
            ],
            "pending": manifest["pending"],
        }
        (hand / "handoff.manifest.json").write_text(json.dumps(src, indent=2))
        paths["handoff"] = hand / "handoff.manifest.json"

    return manifest, paths

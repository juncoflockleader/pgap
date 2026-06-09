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

from . import facade, gltf, instancing, network, props, render
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


_M = 100.0  # metres -> cm


def _sample_height_m(grid, ext, x_m: float, y_m: float) -> float:
    """Bilinear height (metres) from a 2D ``grid`` of metres spanning ``ext`` [w,h]."""
    rows, cols = len(grid), len(grid[0])
    u = min(0.999999, max(0.0, x_m / ext[0])) * (cols - 1)
    w = min(0.999999, max(0.0, y_m / ext[1])) * (rows - 1)
    x0, y0 = int(u), int(w)
    x1, y1 = min(cols - 1, x0 + 1), min(rows - 1, y0 + 1)
    fx, fy = u - x0, w - y0
    g = grid
    top = g[y0][x0] * (1 - fx) + g[y0][x1] * fx
    bot = g[y1][x0] * (1 - fx) + g[y1][x1] * fx
    return float(top * (1 - fy) + bot * fy)


def _apply_terrain(layout: Dict[str, Any], terrain) -> None:
    """FR7: consume a pgap-landscape tile's extent/sea level (+ optional height grid)
    so the city sits on real ground — set per-instance Z (and offset to the tile
    origin). Flat at sea level if no height grid is supplied."""
    if not terrain:
        return
    ox, oy = terrain.get("originM", [0.0, 0.0])
    base_z = float(terrain.get("seaLevelM", 0.0)) * _M
    grid, ext = terrain.get("heightGrid"), terrain.get("extentM")
    layout["terrain"] = terrain
    for coll in (layout["instances"], layout.get("road_instances", []),
                 layout.get("prop_instances", [])):
        for it in coll:
            lx, ly = it["x"] / _M, it["y"] / _M          # city-local metres
            z = base_z + (_sample_height_m(grid, ext, lx, ly) * _M if grid and ext else 0.0)
            it["z"] = round(it.get("z", 0.0) + z, 1)
            it["x"] = round(it["x"] + ox * _M, 1)
            it["y"] = round(it["y"] + oy * _M, 1)


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

    layout = network.generate_layout(profile, s["sizeBlocks"], int(s["seed"]),
                                     float(s["density"]), landmarks=s.get("landmarks") or [])
    layout["name"] = name
    layout["cell"] = f"{era}x{culture}"
    _apply_terrain(layout, s.get("terrain"))   # FR7: sit the city on a landscape tile
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
    # Road kit: one textured slab (road surface on top, dark curb on the sides),
    # reusing the building skinner. HISM-instanced per street segment.
    road_path = None
    if layout.get("road_instances"):
        rrng = np.random.default_rng((int(s["seed"]) ^ zlib.crc32(b"road")) & 0xFFFFFFFF)
        line = (220, 220, 226) if (era == "futuristic" or culture == "japan") else (235, 200, 60)
        road_base, road_nrm = facade.synth_road(fstyle, rrng, line=line)
        curb = np.full((8, 8, 3), (30, 30, 34), dtype=np.uint8)
        curb_n = np.full((8, 8, 3), (128, 128, 255), dtype=np.uint8)
        rp = out / "SM_road_Surface.png"
        write_rgb8(str(rp), road_base)
        texture_paths.append(rp)
        road_path = out / "SM_road.gltf"
        road_path.write_bytes(gltf.building_gltf(
            encode_rgb8(curb), encode_rgb8(curb_n), encode_rgb8(road_base),
            encode_rgb8(road_nrm), roughness=0.96, name="SM_road"))
        paths["kit_road"] = road_path
        kits_meta.append({"id": "road", "mesh": road_path.name, "zone": "road"})

    # Prop kits: one small proxy mesh per distinct prop kind used in the scatter.
    prop_paths: Dict[str, Path] = {}
    for pk in sorted({i["kit"] for i in layout.get("prop_instances", [])}):
        kind = pk[len("prop_"):]
        pp = out / f"SM_{pk}.gltf"
        pp.write_bytes(gltf.prop_gltf(props.prop_parts(kind, fstyle), name=f"SM_{pk}"))
        prop_paths[pk] = pp
        paths[f"kit_{pk}"] = pp
        kits_meta.append({"id": pk, "mesh": pp.name, "zone": "prop", "kind": kind})

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
                   *kit_meshes.values(), *texture_paths,
                   *( [road_path] if road_path else [] ), *prop_paths.values())},
        "roles": {
            "CityLayout": layout_path.name,
            "StyleMaterialSpec": style_path.name,
            "CityInstancing": instancing_path.name,
            **{f"BuildingKit:{kit}": kit_meshes[kit].name for kit in kit_ids},
            **({"RoadNetwork": road_path.name} if road_path else {}),
            **{f"PropKit:{pk[len('prop_'):]}": prop_paths[pk].name for pk in sorted(prop_paths)},
        },
        "counts": {**layout["counts"], "kits": len(kit_ids),
                   "propKits": len(prop_paths), "roadKit": int(road_path is not None)},
        "pending": [],
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
                *([{"role": "RoadNetwork", "file": road_path.name}] if road_path else []),
                *[{"role": f"PropKit:{pk[len('prop_'):]}", "file": prop_paths[pk].name}
                  for pk in sorted(prop_paths)],
            ],
            "pending": manifest["pending"],
        }
        (hand / "handoff.manifest.json").write_text(json.dumps(src, indent=2))
        paths["handoff"] = hand / "handoff.manifest.json"

    return manifest, paths

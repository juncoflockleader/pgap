"""Generate landscape outputs from a spec (L0: heightmap + sidecar + manifest).

L1+ adds weightmaps, tiling textures, scatter rules, water, and the --handoff
source manifest with the full role set (see PRD.md). For now we emit a valid
16-bit heightmap, the import sidecar, and a manifest so the engine round-trip can
be stood up on the `plain` biome.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from . import field, surfacing, texture
from . import scatter as scatter_mod
from .capabilities import (
    SKY_PROFILE_BY_BIOME,
    SUBMERGED_TARGET_BY_BIOME,
    WATER_BY_BIOME,
    WATER_COLOR_BY_BIOME,
)
from .pngio import write_gray8, write_gray16, write_rgb8
from .spec import validate_spec

GENERATOR_VERSION = "0.2.0"


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _spec_hash(normalized: Dict[str, Any]) -> str:
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def generate(spec: Dict[str, Any], out_dir: str | Path, *, handoff: bool = False) -> Tuple[Dict[str, Any], Dict[str, Path]]:
    v = validate_spec(spec)
    if not v["ok"]:
        raise ValueError("invalid landscape spec: " + "; ".join(v["errors"]))
    s = v["normalized"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = str(s["name"])
    biome = s["biome"]

    rng = np.random.Generator(np.random.PCG64(int(s["seed"])))
    res = int(s["resolution"])
    height = field.height_for_biome(rng, res, biome, float(s["ruggedness"]))
    height16 = np.clip(height * 65535.0, 0, 65535).astype(np.uint16)

    paths: Dict[str, Path] = {}
    height_path = out / f"{name}_Height.png"
    write_gray16(str(height_path), height16)
    paths["heightmap"] = height_path

    # L4 water: ocean/shore get a sea level. If the spec leaves it at 0 (sentinel),
    # derive it from the field so a target fraction is submerged regardless of seed
    # (the gradient/basin keeps that submerged part on one side = a coastline).
    water = WATER_BY_BIOME.get(biome, False)
    sea = float(s["seaLevel"])
    if water and sea <= 0.0:
        sea = float(np.percentile(height, SUBMERGED_TARGET_BY_BIOME[biome] * 100.0))

    # L1 surfacing: per-layer weightmaps derived by rule from slope/altitude (the
    # beach bands key off the *effective* sea level so wet/dry sand meet the water).
    layers = list(s["layers"])
    weights, deriv = surfacing.weightmaps(height, biome, layers, sea)
    weight_files: Dict[str, str] = {}
    # L5 tiling textures get their own RNG so they don't perturb the scatter stream.
    tex_rng = np.random.Generator(np.random.PCG64(int(s["seed"]) ^ 0x7e5715))
    tex_files: Dict[str, tuple] = {}
    for layer in layers:
        wpath = out / f"{name}_Weight_{layer}.png"
        write_gray8(str(wpath), np.clip(weights[layer] * 255.0 + 0.5, 0, 255).astype(np.uint8))
        weight_files[layer] = wpath.name
        paths[f"weight_{layer}"] = wpath
        # seamless per-layer base-color + normal map (L5)
        base_rgb, normal_rgb = texture.layer_textures(layer, surfacing.layer_color(layer), tex_rng)
        bpath = out / f"T_{layer}_BaseColor.png"
        npath = out / f"T_{layer}_Normal.png"
        write_rgb8(str(bpath), base_rgb)
        write_rgb8(str(npath), normal_rgb)
        tex_files[layer] = (bpath.name, npath.name)
        paths[f"tex_base_{layer}"], paths[f"tex_normal_{layer}"] = bpath, npath

    material_spec = {
        "blend": "weight",                       # weights sum to 1 per texel
        "layerOrder": layers,
        "layers": [
            {"name": layer, "color": surfacing.layer_color(layer),
             "weightmap": weight_files[layer],
             "baseColor": tex_files[layer][0], "normal": tex_files[layer][1]}
            for layer in layers
        ],
        "rule": "weights are a deterministic function of slope+altitude (no hand-paint)",
        "tiling": True,
    }

    # L2 scatter: foliage/prop rules + a baked point list, derived from the same
    # derivatives the weightmaps use (so plants track the terrain), referencing
    # pgap-3d-actor assets by role.
    scatter_data = scatter_mod.scatter(height, deriv, weights, biome, s["scatter"], rng)
    scatter_path = out / f"{name}.scatter.json"
    scatter_path.write_text(json.dumps(scatter_data, indent=2))
    paths["scatter"] = scatter_path

    # L4 WaterPlane spec (ocean/shore): a flat water surface at sea level, with
    # color + foam hints the bridge's water tool realizes. Submerged fraction is
    # how much of the tile sits at/below the waterline.
    if water:
        submerged = float((height <= sea).mean())
        water_spec = {
            "enabled": True,
            "seaLevel": round(sea, 4),
            "seaLevelM": round(sea * float(s["heightScaleM"]), 1),
            "color": list(WATER_COLOR_BY_BIOME.get(biome, (28, 70, 100))),
            "foam": True,
            "foamWidthM": round(0.01 * float(s["sizeKm"]) * 1000.0, 1),
            "submergedFraction": round(submerged, 3),
            "extentKm": s["sizeKm"],
        }
    else:
        water_spec = {"enabled": False}

    sidecar = {
        "schemaVersion": "psl.landscape.import.v1",
        "name": name,
        "biome": biome,
        "sizeKm": s["sizeKm"],
        "resolution": res,
        "heightScaleM": s["heightScaleM"],
        "seaLevel": round(sea, 4),
        "layers": s["layers"],
        "materialSpec": material_spec,    # L1: layer order + colors + weightmaps
        "scatter": {                      # L2: foliage rules + baked points (sidecar file)
            "density": s["scatter"]["density"],
            "rules": scatter_data["rules"],
            "counts": scatter_data["counts"],
            "points": scatter_path.name,
        },
        "water": water_spec,              # L4: WaterPlane spec
        "skyProfile": SKY_PROFILE_BY_BIOME.get(biome, "clear_day"),
        "palette": s.get("palette", ""),
        "pending": [],
    }
    sidecar_path = out / f"{name}.landscape.import.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    paths["sidecar"] = sidecar_path

    manifest = {
        "schemaVersion": "psl.manifest.v1",
        "name": name,
        "biome": biome,
        "generator": "psl",
        "generatorVersion": GENERATOR_VERSION,
        "seed": int(s["seed"]),
        "specHash": _spec_hash(s),
        "license": "procedurally generated original work",
        "files": {p.name: _sha1(p) for p in (
            height_path, sidecar_path, scatter_path,
            *[paths[f"weight_{layer}"] for layer in layers],
            *[paths[f"tex_base_{layer}"] for layer in layers],
            *[paths[f"tex_normal_{layer}"] for layer in layers])},
        "roles": {
            "Heightmap": height_path.name,
            "LandscapeMaterialSpec": sidecar_path.name,
            "FoliageRule": scatter_path.name,
            **({"WaterPlane": sidecar_path.name} if water else {}),
            **{f"Weightmap:{layer}": weight_files[layer] for layer in layers},
        },
        "warnings": v["warnings"],
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    paths["manifest"] = manifest_path

    if handoff:
        # The unreal-mcp-rx source manifest with every role pgap emits (the bridge
        # realizes them: import heightmap, paint weightmaps, scatter foliage, place
        # the water plane). Tiling layer textures are the remaining role (L5).
        hand = out / "handoff"
        hand.mkdir(exist_ok=True)
        src = {
            "schemaVersion": "game.interactive_component_agent_source_manifest.v1",
            "name": name,
            "roles": [
                {"role": "Heightmap", "file": height_path.name},
                {"role": "LandscapeMaterialSpec", "file": sidecar_path.name},
                {"role": "FoliageRule", "file": scatter_path.name},
                *([{"role": "WaterPlane", "file": sidecar_path.name}] if water else []),
                *[{"role": f"Weightmap:{layer}", "file": weight_files[layer]} for layer in layers],
            ],
            "sidecar": sidecar_path.name,
            "pending": sidecar["pending"],
        }
        (hand / "handoff.manifest.json").write_text(json.dumps(src, indent=2))
        paths["handoff"] = hand / "handoff.manifest.json"

    return manifest, paths

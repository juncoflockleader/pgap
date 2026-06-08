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

from . import network
from .spec import validate_spec
from .styles import MODULE_KINDS, profile_for

GENERATOR_VERSION = "0.0.0"


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
    # kit variant ids referenced by instances (meshes themselves are C1)
    layout["kitsPending"] = sorted({inst["kit"] for inst in layout["instances"]})

    paths: Dict[str, Path] = {}
    layout_path = out / f"{name}.city.layout.json"
    layout_path.write_text(json.dumps(layout, indent=2))
    paths["layout"] = layout_path

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
        "files": {p.name: _sha1(p) for p in (layout_path, style_path)},
        "roles": {"CityLayout": layout_path.name, "StyleMaterialSpec": style_path.name},
        "counts": layout["counts"],
        "pending": ["BuildingKit:<id>", "RoadNetwork", "PropScatter"],
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
            ],
            "pending": manifest["pending"],
        }
        (hand / "handoff.manifest.json").write_text(json.dumps(src, indent=2))
        paths["handoff"] = hand / "handoff.manifest.json"

    return manifest, paths

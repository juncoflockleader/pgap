"""spec dict -> validate (fail closed) -> seeded render -> PNG + manifest."""

from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .background import render_background
from .capabilities import SCHEMA_VERSION, validate_spec
from .png import write_png
from .portrait import render_portrait
from .rng import make_rng
from .spec import spec_from_dict


def default_name(spec) -> str:
    if spec.kind == "portrait":
        return f"{spec.archetype}_portrait_s{spec.seed}"
    return f"{spec.biome}_bg_s{spec.seed}"


def generate(spec_dict: dict, out_dir: str | Path) -> dict:
    ok, errors = validate_spec(spec_dict)
    if not ok:
        raise ValueError("spec failed validation (fail-closed): " + "; ".join(errors))

    spec = spec_from_dict(spec_dict)
    rng = make_rng(spec.seed)

    if spec.kind == "portrait":
        img = render_portrait(spec, rng)
        role = "Portrait"
    else:
        img = render_background(spec, rng)
        role = "BattleBackdrop"

    name = spec.name or default_name(spec)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    png_path = out / f"{name}.png"
    write_png(png_path, img)

    manifest = {
        "pipeline": "2d",
        "generator": f"pgap-2d v{__version__}",
        "schemaVersion": SCHEMA_VERSION,
        "spec": spec.to_dict(),
        "files": [{
            "path": png_path.name,
            "role": role,
            "width": int(img.shape[1]),
            "height": int(img.shape[0]),
        }],
    }
    (out / f"{name}.manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest

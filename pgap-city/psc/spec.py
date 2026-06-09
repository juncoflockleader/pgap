"""City spec schema + fail-closed validation."""

from __future__ import annotations

from typing import Any, Dict, List

from .styles import STYLE_PROFILES

ERAS = ("modern", "futuristic")
CULTURES = ("american", "japan", "cyberpunk", "steampunk")
# v1 supported (era, culture) cells = the keys of the style registry.
CELLS = tuple(sorted(STYLE_PROFILES.keys()))

DEFAULTS: Dict[str, Any] = {
    "name": "City",
    "era": "modern",
    "culture": "american",
    "seed": 0,
    "sizeBlocks": [4, 4],
    "density": None,          # None -> use the profile default
    "layout": "auto",         # auto -> the profile's streetNet
    "landmarks": [],          # named hero slots, flagged for individual placement
    "terrain": None,          # optional pgap-landscape hook (extent/sea level/heights)
}


def validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return {ok, errors, warnings, normalized}. Fail-closed on unsupported cell."""
    errors: List[str] = []
    warnings: List[str] = []
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (spec or {}).items() if v is not None})

    era = str(out.get("era", "")).strip().lower()
    culture = str(out.get("culture", "")).strip().lower()
    out["era"], out["culture"] = era, culture
    if (era, culture) not in STYLE_PROFILES:
        cells = ", ".join(f"{e}x{c}" for e, c in CELLS)
        errors.append(f"unsupported cell {era}x{culture!r}; v1 supports: {cells}")
        return {"ok": False, "errors": errors, "warnings": warnings, "normalized": out}

    try:
        out["seed"] = int(out["seed"])
    except (TypeError, ValueError):
        errors.append("seed must be an integer")

    size = out.get("sizeBlocks") or [4, 4]
    try:
        cols, rows = int(size[0]), int(size[1])
        if not (1 <= cols <= 16 and 1 <= rows <= 16):
            warnings.append(f"sizeBlocks {size} clamped to [1,16]")
        out["sizeBlocks"] = [max(1, min(16, cols)), max(1, min(16, rows))]
    except (TypeError, ValueError, IndexError):
        errors.append("sizeBlocks must be [cols, rows]")

    prof = STYLE_PROFILES[(era, culture)]
    dens = out.get("density")
    out["density"] = prof["density"] if dens is None else max(0.0, min(1.0, float(dens)))

    if out.get("layout", "auto") == "auto":
        out["layout"] = prof["streetNet"]

    lm = out.get("landmarks") or []
    out["landmarks"] = [str(x) for x in lm if isinstance(x, str)][:8]
    if isinstance(lm, list) and len(out["landmarks"]) < len(lm):
        warnings.append("dropped non-string / surplus (>8) landmarks")

    terr = out.get("terrain")
    if terr is not None:
        if not isinstance(terr, dict):
            warnings.append("terrain ignored: must be an object")
            out["terrain"] = None
        else:
            t = {}
            if isinstance(terr.get("seaLevelM"), (int, float)):
                t["seaLevelM"] = float(terr["seaLevelM"])
            if isinstance(terr.get("extentM"), (list, tuple)) and len(terr["extentM"]) == 2:
                t["extentM"] = [float(terr["extentM"][0]), float(terr["extentM"][1])]
            if isinstance(terr.get("originM"), (list, tuple)) and len(terr["originM"]) == 2:
                t["originM"] = [float(terr["originM"][0]), float(terr["originM"][1])]
            if isinstance(terr.get("heightGrid"), list) and terr["heightGrid"]:
                t["heightGrid"] = terr["heightGrid"]      # 2D rows of metres (optional)
            if isinstance(terr.get("tile"), str):
                t["tile"] = terr["tile"]
            out["terrain"] = t or None

    return {"ok": not errors, "errors": errors, "warnings": warnings, "normalized": out}

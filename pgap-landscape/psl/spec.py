"""Landscape spec schema + fail-closed validation (mirrors pgap-3d-actor)."""

from __future__ import annotations

from typing import Any, Dict, List

# v1 biomes (PRD.md). Unsupported biomes fail closed.
BIOMES = ("plain", "forest", "snow", "ocean", "shore", "moon")

# Default material layers per biome (surfacing is L1; this is the declared vocabulary).
LAYERS_BY_BIOME: Dict[str, List[str]] = {
    "plain": ["grass", "dirt"],
    "forest": ["grass", "dirt", "rock"],
    "snow": ["snow", "rock", "scree"],
    "ocean": ["sand", "rock"],
    "shore": ["wetsand", "sand", "grass", "rock"],
    "moon": ["regolith", "rock"],
}

# Default scatter species (refs to pgap-3d-actor roles) per biome.
SCATTER_BY_BIOME: Dict[str, List[str]] = {
    "plain": ["grass", "boulder"],
    "forest": ["pine", "bush", "boulder"],
    "snow": ["pine", "boulder"],
    "ocean": [],
    "shore": ["palm", "grass", "driftwood"],
    "moon": ["boulder"],
}

# UE-friendly landscape resolutions (N*N+1). Others snap to nearest with a warning.
RESOLUTIONS = (505, 1009, 2017)

DEFAULTS: Dict[str, Any] = {
    "name": "Landscape",
    "biome": "plain",
    "seed": 0,
    "sizeKm": 2.0,
    "resolution": 1009,
    "heightScaleM": 400.0,
    "seaLevel": 0.0,
    "ruggedness": 0.5,
    "palette": "",
}

RANGES = {
    "sizeKm": (0.25, 16.0),
    "heightScaleM": (10.0, 4000.0),
    "seaLevel": (0.0, 1.0),
    "ruggedness": (0.0, 1.0),
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return {ok, errors, warnings, normalized}. Fail-closed on unsupported biome."""
    errors: List[str] = []
    warnings: List[str] = []
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (spec or {}).items() if v is not None})

    biome = str(out.get("biome", "")).strip().lower()
    out["biome"] = biome
    if biome not in BIOMES:
        errors.append(f"unsupported biome {biome!r}; choose from {', '.join(BIOMES)}")
        return {"ok": False, "errors": errors, "warnings": warnings, "normalized": out}

    try:
        out["seed"] = int(out["seed"])
    except (TypeError, ValueError):
        errors.append("seed must be an integer")

    for key, (lo, hi) in RANGES.items():
        try:
            val = float(out[key])
        except (TypeError, ValueError):
            errors.append(f"{key} must be a number")
            continue
        if not (lo <= val <= hi):
            warnings.append(f"{key}={val} clamped to [{lo}, {hi}]")
        out[key] = _clamp(val, lo, hi)

    res = int(out.get("resolution", DEFAULTS["resolution"]))
    if res not in RESOLUTIONS:
        nearest = min(RESOLUTIONS, key=lambda r: abs(r - res))
        warnings.append(f"resolution {res} snapped to UE-friendly {nearest}")
        res = nearest
    out["resolution"] = res

    # Layers: default per biome; drop any unsupported requested layer (warn).
    supported = LAYERS_BY_BIOME[biome]
    requested = out.get("layers")
    if requested:
        kept = [layer for layer in requested if layer in supported]
        for layer in requested:
            if layer not in supported:
                warnings.append(f"layer {layer!r} unavailable for {biome}; dropped")
        out["layers"] = kept or list(supported)
    else:
        out["layers"] = list(supported)

    # Scatter species: default per biome; drop unsupported (warn).
    scatter = out.get("scatter") or {}
    species = scatter.get("species") if isinstance(scatter, dict) else None
    default_species = SCATTER_BY_BIOME[biome]
    if species:
        kept = [s for s in species if s in default_species]
        for s in species:
            if s not in default_species:
                warnings.append(f"scatter species {s!r} unavailable for {biome}; dropped")
        species = kept
    else:
        species = list(default_species)
    out["scatter"] = {
        "density": _clamp(float((scatter or {}).get("density", 0.4)), 0.0, 1.0),
        "species": species,
    }

    return {"ok": not errors, "errors": errors, "warnings": warnings, "normalized": out}

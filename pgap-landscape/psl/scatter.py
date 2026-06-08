"""Scatter-by-rule (PRD §6, L2): deterministic foliage/prop placement derived from
the *same* field derivatives the weightmaps use, so plants/rocks can never diverge
from the terrain (no pine on a cliff, no boulder underwater).

Emits two things per species (the PRD L2 decision — rules primary, points fallback):
  1. a **rule** (layer affinity + slope/altitude bands + density + scale) the engine
     /PCG places against the real landscape, referencing a `pgap-3d-actor` asset by
     **role**;
  2. a **baked point list** — `[u, v, height01, yawDeg, scale]` per instance,
     stratified-jittered and density-rejection-sampled from the seeded RNG, for any
     consumer without a procedural-foliage system.
"""

from __future__ import annotations

import numpy as np

# species -> placement rule + the pgap-3d-actor asset role it references.
# `available`: whether 3d-actor can supply it today (only the prop rock = boulder).
SPECIES_RULES = {
    "boulder":   {"layers": ["rock", "scree", "dirt"], "slopeMax": 1.0, "altBand": [0.0, 1.0],
                  "density": 0.22, "scale": [0.7, 1.7], "role": "prop:rock", "available": True},
    "pine":      {"layers": ["grass", "dirt"], "slopeMax": 0.40, "altBand": [0.18, 0.85],
                  "density": 0.55, "scale": [0.8, 1.5], "role": "tree:pine", "available": False},
    "bush":      {"layers": ["grass"], "slopeMax": 0.50, "altBand": [0.10, 0.70],
                  "density": 0.45, "scale": [0.5, 1.1], "role": "foliage:bush", "available": False},
    "grass":     {"layers": ["grass"], "slopeMax": 0.35, "altBand": [0.0, 0.70],
                  "density": 0.80, "scale": [0.5, 1.0], "role": "foliage:grass", "available": False},
    "palm":      {"layers": ["sand", "grass"], "slopeMax": 0.30, "altBand": [0.0, 0.55],
                  "density": 0.30, "scale": [0.9, 1.4], "role": "tree:palm", "available": False},
    "driftwood": {"layers": ["wetsand", "sand"], "slopeMax": 0.40, "altBand": [0.0, 0.40],
                  "density": 0.20, "scale": [0.6, 1.2], "role": "prop:driftwood", "available": False},
}

_MAX_CANDIDATES = 4096  # cap the baked grid so the point list stays bounded


def _density_field(rule: dict, deriv: dict, weights: dict) -> np.ndarray:
    """Per-texel placement probability for a species from the rules + weightmaps."""
    slope, alt = deriv["slope"], deriv["altitude"]
    d = np.zeros_like(slope)
    for layer in rule["layers"]:
        if layer in weights:
            d = d + weights[layer]              # likes these material layers
    d = d * (slope <= rule["slopeMax"])         # not on steep ground
    lo, hi = rule["altBand"]
    d = d * ((alt >= lo) & (alt <= hi))         # within altitude band
    return np.clip(d * float(rule["density"]), 0.0, 1.0)


def _sample_points(density: np.ndarray, height: np.ndarray, rule: dict,
                   global_density: float, rng) -> list:
    """Stratified-jittered, density-rejection-sampled instances (deterministic)."""
    res = density.shape[0]
    peak = float(density.max())
    if peak <= 1e-6 or global_density <= 0:
        return []
    cells = int(np.clip(round((global_density * 80.0)), 6, int(np.sqrt(_MAX_CANDIDATES))))
    lo, hi = rule["scale"]
    pts = []
    for gy in range(cells):
        for gx in range(cells):
            u = (gx + rng.random()) / cells
            vv = (gy + rng.random()) / cells
            ix = min(res - 1, int(u * res))
            iy = min(res - 1, int(vv * res))
            accept = rng.random()
            yaw = rng.random()
            sc = rng.random()
            if accept < density[iy, ix]:
                pts.append([round(u, 4), round(vv, 4), round(float(height[iy, ix]), 4),
                            round(yaw * 360.0, 1), round(lo + (hi - lo) * sc, 3)])
    return pts


def scatter(height: np.ndarray, deriv: dict, weights: dict, biome: str,
            scatter_spec: dict, rng) -> dict:
    """Return {rules: [...], points: {species: [...]}, counts: {...}}."""
    species = [s for s in scatter_spec.get("species", []) if s in SPECIES_RULES]
    global_density = float(scatter_spec.get("density", 0.4))
    rules, points, counts = [], {}, {}
    for name in species:                         # fixed order → deterministic RNG
        rule = SPECIES_RULES[name]
        field = _density_field(rule, deriv, weights)
        pts = _sample_points(field, height, rule, global_density, rng)
        points[name] = pts
        counts[name] = len(pts)
        rules.append({
            "species": name, "role": rule["role"], "source": "pgap-3d-actor",
            "available": rule["available"], "layers": rule["layers"],
            "slopeMax": rule["slopeMax"], "altBand": rule["altBand"],
            "density": round(rule["density"] * global_density, 4), "scale": rule["scale"],
        })
    return {"rules": rules, "points": points, "counts": counts,
            "format": "uv_height01_yawDeg_scale"}

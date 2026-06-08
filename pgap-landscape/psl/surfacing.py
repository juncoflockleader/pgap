"""Surfacing-by-rule (PRD §5, L1): per-layer weightmaps as a pure function of the
height field's derivatives — slope, altitude, sea level — so the material masks can
never disagree with the terrain (no hand-painting).

Each material layer declares an *affinity* over (slope, altitude); the layers are
stacked and normalized per texel so the weights sum to 1 (FR3). Deterministic,
numpy only.
"""

from __future__ import annotations

import numpy as np


# Per-layer stylized base color (sRGB 0..255) — the LandscapeMaterialSpec hint the
# bridge uses to build the layer-blend material.
LAYER_COLORS = {
    "grass": (92, 128, 56), "dirt": (110, 84, 54), "rock": (116, 110, 104),
    "scree": (142, 136, 126), "snow": (236, 240, 250), "sand": (212, 196, 150),
    "wetsand": (168, 148, 112), "regolith": (128, 126, 122),
}


def layer_color(layer: str):
    return list(LAYER_COLORS.get(layer, (128, 128, 128)))


def _smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def derivatives(height: np.ndarray) -> dict:
    """slope (0..1 normalized gradient magnitude), altitude (=height), curvature."""
    gy, gx = np.gradient(height.astype(np.float64))
    slope = np.sqrt(gx * gx + gy * gy)
    slope = slope / (np.percentile(slope, 99.0) + 1e-9)  # robust normalize
    slope = np.clip(slope, 0.0, 1.0)
    curv = np.gradient(gx, axis=1) + np.gradient(gy, axis=0)
    return {"slope": slope, "altitude": height.astype(np.float64), "curvature": curv}


def _affinity(layer: str, slope: np.ndarray, alt: np.ndarray, sea: float) -> np.ndarray:
    """Un-normalized per-texel affinity for a material layer (0..~1)."""
    flat = 1.0 - _smoothstep(0.22, 0.5, slope)        # how flat the texel is
    steep = _smoothstep(0.32, 0.62, slope)
    high = _smoothstep(0.55, 0.8, alt)
    low = 1.0 - _smoothstep(0.45, 0.75, alt)
    ones = np.ones_like(slope)

    if layer == "rock":
        return 0.15 + steep
    if layer == "scree":
        return _smoothstep(0.2, 0.45, slope) * (1.0 - _smoothstep(0.6, 0.85, slope))
    if layer == "snow":
        return high * flat
    if layer == "grass":
        return flat * low
    if layer == "dirt":
        return 0.3 * ones                              # mid-ground fallback
    if layer == "regolith":
        return 0.7 * ones                              # moon: regolith everywhere
    if layer in ("sand", "wetsand"):
        center = sea + (0.05 if layer == "sand" else 0.0)
        width = 0.05 if layer == "wetsand" else 0.08
        return np.exp(-(((alt - center) / width) ** 2))  # band near the shoreline
    return 0.2 * ones


def weightmaps(height: np.ndarray, biome: str, layers: list[str], sea_level: float):
    """Return ({layer: weight[res,res] in [0,1], normalized to sum=1}, derivatives)."""
    d = derivatives(height)
    slope, alt = d["slope"], d["altitude"]
    raw = [np.clip(_affinity(L, slope, alt, float(sea_level)), 0.0, None) for L in layers]
    stack = np.stack(raw, axis=0)
    total = stack.sum(axis=0) + 1e-6
    norm = stack / total
    return {L: norm[i] for i, L in enumerate(layers)}, d

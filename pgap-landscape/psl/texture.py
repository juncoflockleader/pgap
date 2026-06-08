"""Tiling layer textures (PRD §6, L5): a seamless base-color + tangent-space normal
map per material layer, so the bridge's layer-blend material shows real surfaces
(grass speckle, cracked rock, sand ripples, smooth snow) instead of flat colors.

Same technique as pgap-3d-actor's surface synth (procedural pattern → albedo
modulation + height→normal), kept self-contained here. Everything is **tileable**
(periodic noise + wrap-around gradients), deterministic, numpy only.
"""

from __future__ import annotations

import numpy as np

TEX_SIZE = 256

# layer -> {kind, cells, octaves, strength (normal bite), tint (albedo contrast)}.
LAYER_TEX = {
    "grass":    {"kind": "speckle", "cells": 22, "oct": 2, "strength": 0.6, "tint": 0.30},
    "dirt":     {"kind": "speckle", "cells": 14, "oct": 2, "strength": 0.7, "tint": 0.34},
    "rock":     {"kind": "cracks",  "cells": 9,  "oct": 2, "strength": 1.7, "tint": 0.34},
    "scree":    {"kind": "speckle", "cells": 26, "oct": 2, "strength": 1.1, "tint": 0.40},
    "snow":     {"kind": "smooth",  "cells": 6,  "oct": 2, "strength": 0.35, "tint": 0.14},
    "sand":     {"kind": "ripples", "cells": 10, "oct": 2, "strength": 0.7, "tint": 0.18},
    "wetsand":  {"kind": "ripples", "cells": 8,  "oct": 2, "strength": 0.5, "tint": 0.22},
    "regolith": {"kind": "speckle", "cells": 16, "oct": 2, "strength": 0.8, "tint": 0.30},
}


def _smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def _norm01(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(a)


def _tileable_noise(rng: np.random.Generator, size: int, cells: int) -> np.ndarray:
    """Periodic (wrapping) value noise — tiles seamlessly."""
    g = rng.random((cells, cells))
    coords = np.linspace(0.0, cells, size, endpoint=False)
    i0 = np.floor(coords).astype(int) % cells
    i1 = (i0 + 1) % cells
    f = _smoothstep(coords - np.floor(coords))
    col = g[:, i0] * (1 - f)[None, :] + g[:, i1] * f[None, :]   # (cells, size)
    return col[i0, :] * (1 - f)[:, None] + col[i1, :] * f[:, None]


def _tileable_fbm(rng: np.random.Generator, size: int, cells: int, octaves: int) -> np.ndarray:
    out = np.zeros((size, size), dtype=np.float64)
    amp, total, c = 1.0, 0.0, float(cells)
    for _ in range(max(1, octaves)):
        out += amp * _tileable_noise(rng, size, int(round(c)))
        total += amp
        amp *= 0.5
        c *= 2.0
    return _norm01(out / total)


def _pattern(kind: str, rng: np.random.Generator, size: int, cells: int, octaves: int) -> np.ndarray:
    base = _tileable_fbm(rng, size, cells, octaves)
    if kind == "cracks":
        return 1.0 - np.abs(2.0 * base - 1.0)                  # ridged crack network
    if kind == "ripples":
        x = np.linspace(0.0, 2.0 * np.pi * cells, size, endpoint=False)[None, :]
        return _norm01(0.5 + 0.5 * np.sin(x + 3.0 * (base - 0.5)))  # dunes warped by noise
    return base                                                # speckle / smooth


def _height_to_normal(height: np.ndarray, strength: float) -> np.ndarray:
    h = height.astype(np.float64)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -dx * strength, -dy * strength, np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx * inv, ny * inv, nz * inv], axis=-1)
    return (np.clip(n * 0.5 + 0.5, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def layer_textures(layer: str, color, rng: np.random.Generator, size: int = TEX_SIZE):
    """Return (base_color_rgb[H,W,3] uint8, normal_rgb[H,W,3] uint8) for a layer."""
    p = LAYER_TEX.get(layer, LAYER_TEX["dirt"])
    pat = _pattern(p["kind"], rng, size, p["cells"], p["oct"])
    tint = p["tint"]
    mult = (1.0 - tint) + 2.0 * tint * pat
    base = np.clip(np.asarray(color, dtype=np.float64)[None, None, :] / 255.0 * mult[:, :, None],
                   0.0, 1.0)
    base_rgb = (base * 255.0 + 0.5).astype(np.uint8)
    normal_rgb = _height_to_normal(pat, p["strength"])
    return base_rgb, normal_rgb

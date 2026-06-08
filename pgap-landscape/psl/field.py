"""Deterministic height-field synthesis (numpy only).

L0 ships value-noise fBm — enough for the `plain` biome and a generic base for the
others. Ridged/Worley multifractal, domain warp, erosion, and crater stamps are
later milestones (see PRD.md §6). Every function is a pure function of a seeded
``numpy.random.Generator`` so output is byte-identical for a given seed.
"""

from __future__ import annotations

import numpy as np


def _smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def _value_noise(rng: np.random.Generator, res: int, cells: int) -> np.ndarray:
    """Bilinear, smoothstepped value noise on a ``cells``-grid upsampled to res²."""
    cells = max(1, int(cells))
    grid = rng.random((cells + 1, cells + 1))
    coords = np.linspace(0.0, cells, res)
    i0 = np.clip(np.floor(coords).astype(int), 0, cells - 1)
    frac = _smoothstep(coords - i0)
    fy = frac[:, None]
    fx = frac[None, :]
    g00 = grid[i0][:, i0]
    g01 = grid[i0][:, i0 + 1]
    g10 = grid[i0 + 1][:, i0]
    g11 = grid[i0 + 1][:, i0 + 1]
    top = g00 * (1.0 - fx) + g01 * fx
    bot = g10 * (1.0 - fx) + g11 * fx
    return top * (1.0 - fy) + bot * fy


def fbm(
    rng: np.random.Generator,
    res: int,
    *,
    octaves: int = 5,
    base_cells: int = 4,
    gain: float = 0.5,
    lacunarity: float = 2.0,
) -> np.ndarray:
    """Fractal Brownian motion in [0, 1], res × res."""
    out = np.zeros((res, res), dtype=np.float64)
    amp = 1.0
    cells = float(base_cells)
    total = 0.0
    for _ in range(max(1, octaves)):
        out += amp * _value_noise(rng, res, int(round(cells)))
        total += amp
        amp *= gain
        cells *= lacunarity
    out /= total
    lo, hi = float(out.min()), float(out.max())
    if hi - lo > 1e-9:
        out = (out - lo) / (hi - lo)
    return out


# Per-biome fBm tuning. Landforms specific to each biome (ridged peaks for snow,
# craters for moon, sub-sea-level basins for ocean) are TODO L3–L5; for now the
# `ruggedness` knob scales octave detail so every biome is at least previewable.
BIOME_FBM = {
    "plain": dict(octaves=4, base_cells=3, gain=0.45),
    "forest": dict(octaves=5, base_cells=4, gain=0.5),
    "snow": dict(octaves=6, base_cells=5, gain=0.55),
    "ocean": dict(octaves=4, base_cells=3, gain=0.4),
    "shore": dict(octaves=5, base_cells=4, gain=0.45),
    "moon": dict(octaves=6, base_cells=6, gain=0.5),
}


def height_for_biome(rng: np.random.Generator, res: int, biome: str, ruggedness: float) -> np.ndarray:
    params = dict(BIOME_FBM.get(biome, BIOME_FBM["plain"]))
    # ruggedness (0..1) nudges octave count for more/less fine detail, deterministically.
    params["octaves"] = int(round(params["octaves"] * (0.6 + 0.8 * float(ruggedness))))
    return fbm(rng, res, **params)

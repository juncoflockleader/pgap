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


def _norm01(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(a)


def ridged(rng: np.random.Generator, res: int, *, octaves: int = 6,
           base_cells: int = 4, gain: float = 0.55, lacunarity: float = 2.0) -> np.ndarray:
    """Ridged multifractal in [0,1] — sharp crests/valleys (mountain ranges)."""
    out = np.zeros((res, res), dtype=np.float64)
    amp, cells, total, weight = 1.0, float(base_cells), 0.0, 1.0
    for _ in range(max(1, octaves)):
        signal = 1.0 - np.abs(2.0 * _value_noise(rng, res, int(round(cells))) - 1.0)
        signal = signal * signal                       # sharpen the ridge
        out += signal * amp * np.clip(weight, 0.0, 1.0)
        weight = signal                                # multifractal weighting
        total += amp
        amp *= gain
        cells *= lacunarity
    return _norm01(out / max(total, 1e-9))


def _bilinear_sample(arr: np.ndarray, yy: np.ndarray, xx: np.ndarray) -> np.ndarray:
    res = arr.shape[0]
    yy = np.clip(yy, 0, res - 1); xx = np.clip(xx, 0, res - 1)
    y0 = np.floor(yy).astype(int); x0 = np.floor(xx).astype(int)
    y1 = np.minimum(y0 + 1, res - 1); x1 = np.minimum(x0 + 1, res - 1)
    fy = yy - y0; fx = xx - x0
    top = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    bot = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def domain_warp(base: np.ndarray, wx: np.ndarray, wy: np.ndarray, amp: float) -> np.ndarray:
    """Resample ``base`` at coordinates displaced by (wx, wy) — organic, un-gridded."""
    res = base.shape[0]
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float64)
    return _bilinear_sample(base, yy + (wy * 2 - 1) * amp, xx + (wx * 2 - 1) * amp)


def thermal_erosion(h: np.ndarray, *, iterations: int = 10, strength: float = 0.2,
                    percentile: float = 88.0) -> np.ndarray:
    """Cheap thermal (talus) erosion: only the *steepest* slopes (above a per-step
    percentile talus) slide downhill to lower neighbors — so it carves ridges/valleys
    instead of diffusing the whole field flat. Resolution-adaptive, mass-conserving,
    bounded iterations → deterministic."""
    h = h.astype(np.float64).copy()
    shifts = [(1, 0), (-1, 0), (1, 1), (-1, 1)]
    for _ in range(max(0, iterations)):
        drop = [np.clip(h - np.roll(h, sh, ax), 0.0, None) for sh, ax in shifts]
        steepest = np.maximum.reduce(drop)
        pos = steepest[steepest > 1e-9]
        talus = float(np.percentile(pos, percentile)) if pos.size else 0.0
        excess = [np.clip(d - talus, 0.0, None) for d in drop]
        total = np.sum(excess, axis=0)
        h = h - strength * total
        for (sh, ax), e in zip(shifts, excess):
            h = h + np.roll(strength * e, -sh, ax)      # deposit on the lower neighbor
    return _norm01(h)


def height_for_biome(rng: np.random.Generator, res: int, biome: str, ruggedness: float) -> np.ndarray:
    """Per-biome landform composition: warped fBm + ridged crests + thermal erosion."""
    r = float(np.clip(ruggedness, 0.0, 1.0))
    base = fbm(rng, res, octaves=5, base_cells=4, gain=0.5)
    wx = fbm(rng, res, octaves=3, base_cells=3, gain=0.5)
    wy = fbm(rng, res, octaves=3, base_cells=3, gain=0.5)
    warped = domain_warp(base, wx, wy, amp=res * (0.02 + 0.03 * r))
    # Erosion carves *sharp* terrain into talus slopes/valleys; it only helps the
    # ridged biomes. Soft-fBm biomes (plain/moon/ocean) are gentle by design and
    # would just flatten, so they skip it.
    erode = lambda h, it: thermal_erosion(h, iterations=int(it * (0.5 + r)))

    if biome == "snow":                                 # alpine ridges + glacial valleys
        h = erode(0.3 * warped + 0.7 * ridged(rng, res, octaves=6, base_cells=4, gain=0.55), 10)
    elif biome == "forest":                             # rolling hills + a few ridges
        h = erode(0.78 * warped + 0.22 * ridged(rng, res, octaves=4, base_cells=4, gain=0.5), 5)
    elif biome == "ocean":                              # mostly sub-sea-level basin
        h = 0.4 * warped
    elif biome == "shore":                              # land rising away from the sea
        grad = np.linspace(0.0, 1.0, res)[None, :] ** 1.3
        h = _norm01(0.65 * warped * grad + 0.18 * grad)
    elif biome == "moon":                               # gentle base; craters land in L3
        h = warped
    else:                                               # plain: warped rolling hills
        h = warped
    return _norm01(h)

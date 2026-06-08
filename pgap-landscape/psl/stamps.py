"""Stamps (PRD §6, L3): feature stamps composited onto the height field — the
crater field for the moon. A crater is a bowl (central depression) + a raised rim +
a little ejecta apron; many are stamped with a power-law size distribution (lots of
small, few large) so the surface reads as battered regolith. Deterministic (seeded
RNG), local-patch compositing for speed.
"""

from __future__ import annotations

import numpy as np


def _crater_profile(d: np.ndarray) -> np.ndarray:
    """Signed height delta vs normalized radius d = dist/R: bowl + rim + ejecta."""
    bowl = np.where(d < 1.0, d * d - 1.0, 0.0)          # -1 at center → 0 at the rim
    rim = 0.65 * np.exp(-((d - 1.0) * 4.0) ** 2)        # raised ring at d≈1
    ejecta = np.where(d > 1.0, 0.12 * np.exp(-(d - 1.0) * 2.0), 0.0)
    return bowl + rim + ejecta


def crater_field(height: np.ndarray, rng: np.random.Generator, *, count: int = 130,
                 rmin: float = 0.012, rmax: float = 0.13, depth: float = 0.95) -> np.ndarray:
    """Composite ``count`` craters onto ``height`` (NOT normalized — the caller does).

    Radii are a fraction of the tile (resolution-independent); bigger craters are
    deeper. Each crater touches only a local patch, so cost is ~count·patch².
    """
    h = height.astype(np.float64).copy()
    res = h.shape[0]
    for _ in range(max(0, count)):
        R = (rmin + (rmax - rmin) * rng.random() ** 2.4) * res   # power-law: many small
        cx = rng.random() * res
        cy = rng.random() * res
        amp = depth * (R / res)                                  # bigger → deeper
        rad = int(R * 1.7) + 2
        x0, x1 = max(0, int(cx) - rad), min(res, int(cx) + rad)
        y0, y1 = max(0, int(cy) - rad), min(res, int(cy) + rad)
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
        d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2) / R
        h[y0:y1, x0:x1] += amp * _crater_profile(d)
    return h

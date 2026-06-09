"""Facade skin synthesis — the building "skin".

Turns a style facade spec (wall/trim/glass/roof colors, window rhythm, ground-floor
style, optional emissive lit windows) into base-color + normal (+ emissive) texture
maps for a building's walls and roof. Pure numpy + the stdlib PNG writer; seeded and
deterministic. The kit's box mesh UV-maps each wall 0..1 onto the facade and the top
onto the roof (see ``gltf.building_gltf``), so a few small textures skin the skyline.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def _height_to_normal(height: np.ndarray, strength: float = 2.5) -> np.ndarray:
    """A tangent-space normal map (H,W,3 uint8) from a 0..1 height field — recessed
    glass + proud frames read as relief under engine lighting."""
    gy, gx = np.gradient(height.astype(np.float64))
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(height)
    n = np.stack([nx, ny, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    return ((n * 0.5 + 0.5) * 255.0 + 0.5).astype(np.uint8)


def synth_facade(fstyle: dict, cols: int, rows: int, rng,
                 cell: int = 48) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Build (base_rgb, normal, emissive) for a ``cols`` × ``rows`` window grid.

    Row 0 is the ground floor (bottom of the image / building). Returns uint8 arrays;
    ``emissive`` is None when the style has no lit windows. Deterministic given ``rng``."""
    cols, rows = int(max(1, cols)), int(max(1, rows))
    W, H = cols * cell, rows * cell
    wall = np.array(fstyle["wall"], float)
    trim = np.array(fstyle["trim"], float)
    glass = np.array(fstyle["glass"], float)
    emissive_col = fstyle.get("emissive")
    lit_frac = float(fstyle.get("lit_frac", 0.0))
    arch = bool(fstyle.get("arch", False))
    ground = str(fstyle.get("ground", "storefront"))

    base = np.clip(wall[None, None, :] + (rng.random((H, W)) - 0.5)[..., None] * 14.0, 0, 255)
    height = np.full((H, W), 0.5)
    emissive = np.zeros((H, W, 3), float)

    m = int(cell * (0.24 if arch else 0.18))      # horizontal inset (arches are narrower)
    mv = int(cell * 0.16)                          # vertical inset
    fw = max(1, int(cell * 0.06))                  # frame width

    for f in range(rows):
        y1, y0 = H - f * cell, H - (f + 1) * cell  # image rows for this floor
        gy0, gy1 = y0 + mv, y1 - mv
        storefront = (f == 0 and ground == "storefront")
        for c in range(cols):
            x0 = c * cell
            gx0, gx1 = x0 + m, x0 + cell - m
            wy0 = gy0
            if storefront:                          # tall glass to the floor
                gx0, gx1 = x0 + fw * 2, x0 + cell - fw * 2
                gy1_ = y1 - fw
                wy0 = gy0
            else:
                gy1_ = gy1
            # frame ring (proud trim), then the glass pane (recessed)
            base[wy0 - fw:gy1_ + fw, gx0 - fw:gx1 + fw] = trim
            height[wy0 - fw:gy1_ + fw, gx0 - fw:gx1 + fw] = 0.72
            lit = emissive_col is not None and rng.random() < lit_frac
            pane = np.array(emissive_col, float) if lit else glass
            base[wy0:gy1_, gx0:gx1] = pane
            height[wy0:gy1_, gx0:gx1] = 0.30
            if lit:
                emissive[wy0:gy1_, gx0:gx1] = np.array(emissive_col, float)
            # a simple mullion cross
            mc = (wy0 + gy1_) // 2
            base[mc - 1:mc + 1, gx0:gx1] = trim
            cc = (gx0 + gx1) // 2
            base[wy0:gy1_, cc - 1:cc + 1] = trim

    cap = max(2, int(cell * 0.16))                  # parapet cap at the top
    base[0:cap, :] = trim
    height[0:cap, :] = 0.82

    base_u = base.astype(np.uint8)
    nrm = _height_to_normal(height)
    emis = np.clip(emissive, 0, 255).astype(np.uint8) if emissive_col is not None else None
    return base_u, nrm, emis


def synth_roof(fstyle: dict, rng, px: int = 64) -> Tuple[np.ndarray, np.ndarray]:
    """A simple roof skin (base_rgb, normal): the roof color with subtle panelling."""
    roof = np.array(fstyle["roof"], float)
    base = np.clip(roof[None, None, :] + (rng.random((px, px)) - 0.5)[..., None] * 12.0, 0, 255)
    height = np.full((px, px), 0.5)
    step = max(8, px // 4)                            # faint panel seams
    base[::step, :] *= 0.85
    base[:, ::step] *= 0.85
    height[::step, :] = 0.62
    height[:, ::step] = 0.62
    return base.astype(np.uint8), _height_to_normal(height, 1.5)

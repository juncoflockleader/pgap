"""Headless software renderer — a gear mesh → a preview PNG.

Offline, deterministic: fixed orbit camera, orthographic projection, z-buffer, flat
per-triangle shading using each triangle's *material* base color × a two-term
lambert (hard-edged gear reads better flat-shaded than smoothed). Pure numpy.
"""

from __future__ import annotations

from typing import List

import numpy as np

from .materials import MATERIALS
from .pngio import encode_rgb8


def render_image(pos, nrm, idx, tri_mat: List[str], size: int = 384,
                 az: float = 28.0, el: float = 12.0, light=(0.4, 0.8, 0.5),
                 bg=(0.13, 0.13, 0.15), ambient: float = 0.42) -> np.ndarray:
    pos = np.asarray(pos, dtype=np.float64)
    tris = idx.reshape(-1, 3)
    fn = np.asarray(nrm, dtype=np.float64)

    center = 0.5 * (pos.min(0) + pos.max(0))
    radius = 0.5 * float(np.linalg.norm(pos.max(0) - pos.min(0))) + 1e-6
    a, e = np.radians(az), np.radians(el)
    eyedir = np.array([np.cos(e) * np.cos(a), np.sin(e), np.cos(e) * np.sin(a)])
    fwd = -eyedir
    right = np.cross(fwd, [0, 1.0, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = pos - center
    xs = rel @ right
    ys = rel @ up
    depth = rel @ fwd
    scale = (size * 0.46) / radius
    sx = size * 0.5 + xs * scale
    sy = size * 0.5 - ys * scale

    L = np.asarray(light, float); L /= np.linalg.norm(L)
    col = {m: np.array(MATERIALS.get(m, MATERIALS["iron"])[0]) for m in set(tri_mat)}

    img = np.empty((size, size, 3)); img[:] = bg
    zbuf = np.full((size, size), np.inf)
    # face normal per triangle = average of its vertex normals (flat geometry)
    for t in range(len(tris)):
        i0, i1, i2 = (int(v) for v in tris[t])
        x0, y0 = sx[i0], sy[i0]; x1, y1 = sx[i1], sy[i1]; x2, y2 = sx[i2], sy[i2]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        n = (fn[i0] + fn[i1] + fn[i2]); n /= np.linalg.norm(n) + 1e-9
        lam = max(0.0, float(n @ L))
        base = col[tri_mat[t]]
        rgb = np.clip(base * (ambient + (1 - ambient) * lam), 0, 1)
        minx = max(int(np.floor(min(x0, x1, x2))), 0); maxx = min(int(np.ceil(max(x0, x1, x2))), size - 1)
        miny = max(int(np.floor(min(y0, y1, y2))), 0); maxy = min(int(np.ceil(max(y0, y1, y2))), size - 1)
        if minx > maxx or miny > maxy:
            continue
        yy, xx = np.mgrid[miny:maxy + 1, minx:maxx + 1]
        px, py = xx + 0.5, yy + 0.5
        w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / area
        w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * depth[i0] + w1 * depth[i1] + w2 * depth[i2]
        sub = zbuf[miny:maxy + 1, minx:maxx + 1]
        win = inside & (z < sub)
        sub[win] = z[win]
        img[miny:maxy + 1, minx:maxx + 1][win] = rgb
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def render_png(pos, nrm, idx, tri_mat, size: int = 384, **kw) -> bytes:
    return encode_rgb8(render_image(pos, nrm, idx, tri_mat, size=size, **kw))

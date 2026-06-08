"""Headless software renderer (numpy) — a built mesh → a thumbnail PNG.

Offline and deterministic: no GPU, no engine. We place a fixed orbit camera around
the mesh, orthographically project the triangles, z-buffer rasterize them, and
Gouraud-shade with the mesh's own vertex colors (COLOR_0) times a simple two-term
lambert. Because it shades the *vertex colors*, the thumbnail shows the real coat
plus the eyes/iris/nose/mouth — exactly what the engine renders — with no UE bridge
required. Used by the bestiary catalog (``pgap.catalog``).

Pure numpy, no RNG, fixed iteration order ⇒ byte-identical PNGs for a given mesh.
"""

from __future__ import annotations

import numpy as np

from .texture import _png_rgb
from .types import Mesh

_F = np.float32


def _orbit_dir(az_deg: float, el_deg: float) -> np.ndarray:
    """Unit camera direction. az=0 looks from +X (a creature's front); +az swings
    toward +Z; +el lifts the camera above the horizon."""
    az, el = np.radians(az_deg), np.radians(el_deg)
    d = np.array([np.cos(el) * np.cos(az), np.sin(el), np.cos(el) * np.sin(az)])
    return d / np.linalg.norm(d)


def render_image(mesh: Mesh, size: int = 384, az: float = 35.0, el: float = 16.0,
                 light=(0.5, 0.85, 0.35), bg=(0.11, 0.11, 0.13),
                 ambient: float = 0.48, tint=(1.0, 1.0, 1.0)) -> np.ndarray:
    """Render ``mesh`` to an (size, size, 3) uint8 RGB image (sRGB-ish, no gamma).

    ``tint`` stands in for the base-color texture: the pipeline stores vertex colors
    as ``target / base_coat`` ratios meant to be multiplied by the (≈base-coat) coat
    texture, so passing ``palette.base_coat(material)`` recovers the true region
    colors (golden body, dark eyes, the iris hue, …). Default leaves them raw.
    """
    pos = mesh.positions.astype(np.float64)
    nrm = mesh.normals.astype(np.float64)
    faces = mesh.indices.reshape(-1, 3).astype(np.int64)
    col = (mesh.colors[:, :3].astype(np.float64)
           if mesh.colors is not None else np.full((pos.shape[0], 3), 0.72))
    col = np.clip(col * np.asarray(tint, float), 0.0, 1.0)

    # Fixed orbit camera framing the AABB.
    center = 0.5 * (pos.min(0) + pos.max(0))
    radius = 0.5 * float(np.linalg.norm(pos.max(0) - pos.min(0))) + 1e-6
    eyedir = _orbit_dir(az, el)
    forward = -eyedir
    right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    rel = pos - center
    xc, yc = rel @ right, rel @ up
    depth = rel @ forward                       # smaller = nearer the camera
    scale = (size * 0.42) / radius
    sx = size * 0.5 + xc * scale
    sy = size * 0.5 - yc * scale                # image y points down

    # Per-vertex Gouraud shade: vertex color × (ambient + diffuse·lambert).
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    nlen = np.linalg.norm(nrm, axis=1, keepdims=True)
    unit_n = nrm / np.where(nlen < 1e-9, 1.0, nlen)
    lam = np.clip(unit_n @ L, 0.0, 1.0)
    shaded = np.clip(col * (ambient + (1.0 - ambient) * lam)[:, None], 0.0, 1.0)

    img = np.empty((size, size, 3), dtype=np.float64)
    img[:] = np.asarray(bg, float)
    zbuf = np.full((size, size), np.inf)

    for tri in faces:
        i0, i1, i2 = int(tri[0]), int(tri[1]), int(tri[2])
        x0, y0 = sx[i0], sy[i0]; x1, y1 = sx[i1], sy[i1]; x2, y2 = sx[i2], sy[i2]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        minx = max(int(np.floor(min(x0, x1, x2))), 0)
        maxx = min(int(np.ceil(max(x0, x1, x2))), size - 1)
        miny = max(int(np.floor(min(y0, y1, y2))), 0)
        maxy = min(int(np.ceil(max(y0, y1, y2))), size - 1)
        if minx > maxx or miny > maxy:
            continue
        ys, xs = np.mgrid[miny:maxy + 1, minx:maxx + 1]
        xs = xs + 0.5; ys = ys + 0.5
        w0 = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / area
        w1 = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * depth[i0] + w1 * depth[i1] + w2 * depth[i2]
        sub = zbuf[miny:maxy + 1, minx:maxx + 1]
        win = inside & (z < sub)
        if not win.any():
            continue
        rgb = (w0[..., None] * shaded[i0] + w1[..., None] * shaded[i1]
               + w2[..., None] * shaded[i2])
        sub[win] = z[win]
        img[miny:maxy + 1, minx:maxx + 1][win] = rgb[win]

    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def render_png(mesh: Mesh, size: int = 384, **kw) -> bytes:
    """Render ``mesh`` and return PNG bytes."""
    return _png_rgb(render_image(mesh, size=size, **kw))

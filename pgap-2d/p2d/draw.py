"""Soft-edged numpy rasterizer: ellipses, convex polygons, strokes, gradients.

Everything draws onto a float32 (H, W, 4) premultiply-free RGBA canvas via
"over" compositing with a per-pixel coverage mask (cheap antialiasing).
"""

from __future__ import annotations

import colorsys

import numpy as np

Color = tuple[float, float, float, float]


def canvas(width: int, height: int, color: Color = (0.0, 0.0, 0.0, 0.0)) -> np.ndarray:
    img = np.zeros((height, width, 4), dtype=np.float32)
    img[...] = np.asarray(color, dtype=np.float32)
    return img


def hsv(h: float, s: float, v: float, a: float = 1.0) -> Color:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, min(max(s, 0.0), 1.0), min(max(v, 0.0), 1.0))
    return (r, g, b, a)


def _grid(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = img.shape[:2]
    g = np.mgrid[0:h, 0:w].astype(np.float32)
    return g[1], g[0]  # xx, yy


def blend(img: np.ndarray, mask: np.ndarray, color: Color) -> None:
    """Composite `color` over `img` with per-pixel coverage `mask` (0..1)."""
    a = (mask * color[3]).astype(np.float32)
    if float(a.max()) <= 0.0:
        return
    src = np.asarray(color[:3], dtype=np.float32)
    dst_a = img[..., 3]
    out_a = a + dst_a * (1.0 - a)
    safe = np.maximum(out_a, 1e-6)
    img[..., :3] = (src[None, None, :] * a[..., None]
                    + img[..., :3] * (dst_a * (1.0 - a))[..., None]) / safe[..., None]
    img[..., 3] = out_a


def ellipse(img: np.ndarray, cx: float, cy: float, rx: float, ry: float,
            color: Color, feather: float = 1.5, rot: float = 0.0) -> None:
    xx, yy = _grid(img)
    dx, dy = xx - cx, yy - cy
    if rot:
        c, s = np.cos(rot), np.sin(rot)
        dx, dy = c * dx + s * dy, -s * dx + c * dy
    d = np.sqrt((dx / max(rx, 1e-6)) ** 2 + (dy / max(ry, 1e-6)) ** 2)
    mask = np.clip((1.0 - d) * (min(rx, ry) / max(feather, 1e-6)), 0.0, 1.0)
    blend(img, mask, color)


def polygon(img: np.ndarray, pts: list[tuple[float, float]], color: Color,
            feather: float = 1.5) -> None:
    """Convex polygon (any winding); soft edges via min signed distance."""
    p = [(float(x), float(y)) for x, y in pts]
    area = sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
               for i in range(len(p)))
    if area < 0:
        p = p[::-1]
    xx, yy = _grid(img)
    inside = None
    for i in range(len(p)):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % len(p)]
        length = max(np.hypot(x1 - x0, y1 - y0), 1e-6)
        d = ((x1 - x0) * (yy - y0) - (y1 - y0) * (xx - x0)) / length
        inside = d if inside is None else np.minimum(inside, d)
    mask = np.clip(inside / max(feather, 1e-6), 0.0, 1.0)
    blend(img, mask, color)


def stroke(img: np.ndarray, pts: list[tuple[float, float]], width: float,
           color: Color, feather: float = 1.0) -> None:
    """Stamp a polyline as a soft-edged stroke (width = radius in px)."""
    xx, yy = _grid(img)
    dist2 = np.full(img.shape[:2], np.inf, dtype=np.float32)
    for px, py in pts:
        d2 = (xx - px) ** 2 + (yy - py) ** 2
        np.minimum(dist2, d2, out=dist2)
    mask = np.clip((width - np.sqrt(dist2)) / max(feather, 1e-6) + 1.0, 0.0, 1.0)
    blend(img, mask, color)


def bezier(p0, p1, p2, n: int = 48) -> list[tuple[float, float]]:
    t = np.linspace(0.0, 1.0, n)[:, None]
    a = np.asarray(p0, dtype=np.float32)
    b = np.asarray(p1, dtype=np.float32)
    c = np.asarray(p2, dtype=np.float32)
    pts = (1 - t) ** 2 * a + 2 * (1 - t) * t * b + t ** 2 * c
    return [(float(x), float(y)) for x, y in pts]


def vgradient(img: np.ndarray, top: Color, bottom: Color,
              y0: float = 0.0, y1: float | None = None) -> None:
    """Overwrite the canvas with a vertical gradient (used as the base layer)."""
    h = img.shape[0]
    if y1 is None:
        y1 = float(h)
    t = np.clip((np.arange(h, dtype=np.float32)[:, None] - y0) / max(y1 - y0, 1.0), 0.0, 1.0)
    for c in range(4):
        img[..., c] = top[c] * (1.0 - t) + bottom[c] * t


def vignette(img: np.ndarray, strength: float = 0.35) -> None:
    h, w = img.shape[:2]
    xx, yy = _grid(img)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    mask = np.clip((d - 0.7) / 0.5, 0.0, 1.0) * strength
    blend(img, mask, (0.0, 0.0, 0.05, 1.0))

"""Battle backdrop generator — layered parallax-style scenes.

Layer stack: sky gradient -> celestial body / stars -> N ridge silhouettes
(smoothed random-walk skylines) -> ground band -> biome accents -> vignette.
"""

from __future__ import annotations

import numpy as np

from .draw import blend, canvas, ellipse, polygon, vgradient, vignette

BIOMES = {
    "meadow": {
        "sky_top": (0.47, 0.74, 0.95, 1.0), "sky_bot": (0.86, 0.93, 0.84, 1.0),
        "sun": (1.0, 0.95, 0.72), "sun_pos": (0.76, 0.21),
        "hills": [(0.46, 0.66, 0.43), (0.36, 0.57, 0.36), (0.28, 0.48, 0.31)],
        "ground": (0.43, 0.67, 0.39), "ground_dark": (0.32, 0.54, 0.30),
        "accent": "flowers",
    },
    "forest": {
        "sky_top": (0.35, 0.55, 0.62, 1.0), "sky_bot": (0.72, 0.84, 0.70, 1.0),
        "sun": (0.98, 0.95, 0.80), "sun_pos": (0.83, 0.17),
        "hills": [(0.25, 0.45, 0.30), (0.18, 0.37, 0.25), (0.12, 0.29, 0.20)],
        "ground": (0.20, 0.40, 0.24), "ground_dark": (0.13, 0.30, 0.18),
        "accent": "trees",
    },
    "cave": {
        "sky_top": (0.07, 0.06, 0.11, 1.0), "sky_bot": (0.16, 0.13, 0.22, 1.0),
        "sun": None, "sun_pos": (0.5, 0.2),
        "hills": [(0.22, 0.19, 0.30), (0.16, 0.14, 0.23), (0.11, 0.10, 0.17)],
        "ground": (0.20, 0.17, 0.27), "ground_dark": (0.12, 0.10, 0.17),
        "accent": "crystals",
    },
    "night": {
        "sky_top": (0.05, 0.07, 0.18, 1.0), "sky_bot": (0.16, 0.20, 0.38, 1.0),
        "sun": (0.92, 0.94, 1.0), "sun_pos": (0.78, 0.18),
        "hills": [(0.13, 0.17, 0.30), (0.09, 0.12, 0.23), (0.06, 0.09, 0.17)],
        "ground": (0.10, 0.14, 0.22), "ground_dark": (0.06, 0.09, 0.15),
        "accent": "stars",
    },
}


def _ridge_alpha(w: int, h: int, base_y: float, amp: float,
                 rng: np.random.Generator, smooth: int = 28) -> np.ndarray:
    walk = rng.normal(0.0, 1.0, w + smooth * 2).cumsum()
    kernel = np.ones(smooth, dtype=np.float64) / smooth
    walk = np.convolve(walk, kernel, mode="same")[smooth:-smooth]
    span = max(float(walk.max() - walk.min()), 1e-6)
    ridge = base_y + ((walk - walk.min()) / span - 0.5) * amp
    yy = np.arange(h, dtype=np.float32)[:, None]
    return np.clip((yy - ridge[None, :].astype(np.float32)) / 2.0, 0.0, 1.0)


def _poke(img: np.ndarray, xs: np.ndarray, ys: np.ndarray, color, size: int = 1) -> None:
    h, w = img.shape[:2]
    c = np.asarray(color, dtype=np.float32)
    for dy in range(size):
        for dx in range(size):
            x = np.clip(xs + dx, 0, w - 1)
            y = np.clip(ys + dy, 0, h - 1)
            img[y, x, :3] = img[y, x, :3] * (1.0 - c[3]) + c[:3] * c[3]
            img[y, x, 3] = np.maximum(img[y, x, 3], c[3])


def render_background(spec, rng: np.random.Generator) -> np.ndarray:
    w, h = int(spec.width), int(spec.height)
    b = BIOMES[spec.biome]
    img = canvas(w, h)

    vgradient(img, b["sky_top"], b["sky_bot"], 0.0, h * 0.75)

    if b["accent"] in ("stars",) or b["sun"] is None:
        n = 130
        xs = rng.integers(0, w, n)
        ys = rng.integers(0, int(h * 0.55), n)
        _poke(img, xs, ys, (1.0, 1.0, 1.0, 0.8))
        bright = rng.integers(0, n, 18)
        _poke(img, xs[bright], ys[bright], (1.0, 1.0, 1.0, 0.95), size=2)

    if b["sun"] is not None:
        sx, sy = b["sun_pos"][0] * w, b["sun_pos"][1] * h
        r = h * 0.075
        ellipse(img, sx, sy, r * 3.2, r * 3.2, (*b["sun"], 0.18), feather=r * 3.0)
        ellipse(img, sx, sy, r, r, (*b["sun"], 1.0), feather=2.0)
        if spec.biome == "night":
            ellipse(img, sx - r * 0.3, sy - r * 0.2, r * 0.28, r * 0.28,
                    (0.75, 0.78, 0.88, 0.8))
            ellipse(img, sx + r * 0.35, sy + r * 0.3, r * 0.18, r * 0.18,
                    (0.75, 0.78, 0.88, 0.7))

    n_hills = len(b["hills"])
    for i, color in enumerate(b["hills"]):
        base_y = h * (0.45 + 0.13 * i)
        amp = h * (0.16 - 0.035 * i)
        blend(img, _ridge_alpha(w, h, base_y, amp, rng), (*color, 1.0))

    gy = h * 0.74
    yy = np.arange(h, dtype=np.float32)[:, None]
    blend(img, np.clip((yy - gy) / 3.0, 0.0, 1.0) * np.ones((h, w), np.float32),
          (*b["ground"], 1.0))
    blend(img, np.clip((yy - h * 0.86) / (h * 0.14), 0.0, 1.0) * np.ones((h, w), np.float32),
          (*b["ground_dark"], 0.85))

    accent = b["accent"]
    if accent == "flowers":
        n = 110
        xs = rng.integers(0, w, n)
        ys = rng.integers(int(gy) + 8, h - 4, n)
        palette = [(1.0, 1.0, 1.0, 0.9), (1.0, 0.85, 0.35, 0.9), (1.0, 0.62, 0.75, 0.9)]
        for k, color in enumerate(palette):
            _poke(img, xs[k::3], ys[k::3], color, size=2)
    elif accent == "trees":
        for _ in range(6):
            tx = float(rng.uniform(0.05, 0.95)) * w
            ty = h * float(rng.uniform(0.58, 0.70))
            th = h * float(rng.uniform(0.16, 0.26))
            color = (0.08, 0.20, 0.13, 1.0)
            polygon(img, [(tx, ty - th), (tx - th * 0.38, ty), (tx + th * 0.38, ty)], color)
            polygon(img, [(tx - th * 0.05, ty), (tx + th * 0.05, ty),
                          (tx + th * 0.05, ty + th * 0.18), (tx - th * 0.05, ty + th * 0.18)],
                    (0.16, 0.11, 0.08, 1.0))
    elif accent == "crystals":
        for _ in range(5):
            kx = float(rng.uniform(0.08, 0.92)) * w
            ky = h * float(rng.uniform(0.70, 0.88))
            kr = h * float(rng.uniform(0.05, 0.10))
            ellipse(img, kx, ky - kr * 0.4, kr * 2.2, kr * 2.2, (0.45, 0.85, 0.95, 0.16),
                    feather=kr * 2.0)
            polygon(img, [(kx, ky - kr * 1.6), (kx + kr * 0.55, ky), (kx, ky + kr * 0.5),
                          (kx - kr * 0.55, ky)], (0.55, 0.88, 0.97, 0.95))
        for _ in range(8):
            tx = float(rng.uniform(0.02, 0.98)) * w
            tw = w * float(rng.uniform(0.01, 0.03))
            tl = h * float(rng.uniform(0.08, 0.22))
            polygon(img, [(tx - tw, 0), (tx + tw, 0), (tx, tl)], (0.13, 0.11, 0.19, 1.0))

    vignette(img, 0.35)
    return img

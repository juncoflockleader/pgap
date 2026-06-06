"""Color palettes for procedural texture/vertex tint (M4).

Maps a freeform ``material.baseColor`` string to a base coat color plus per-region
target colors (sRGB 0..1). Keyword detection is deliberately coarse — the precise,
open-vocabulary path is the optional image-gen step (deferred). The golden
retriever palette is the reference.
"""

from __future__ import annotations

import numpy as np

_F = np.float32

# region -> target sRGB color, per coat keyword.
_GOLDEN = {
    "body": (0.80, 0.58, 0.30),
    "belly": (0.92, 0.82, 0.62),   # cream chest/underside
    "head": (0.82, 0.60, 0.32),
    "muzzle": (0.86, 0.70, 0.46),  # lighter muzzle
    "ears": (0.46, 0.32, 0.18),    # darker ears
    "legs": (0.88, 0.76, 0.55),    # cream lower-leg feathering
    "tail": (0.85, 0.66, 0.40),    # golden tail, lighter feathering
}
_BROWN = {
    "body": (0.40, 0.26, 0.15), "belly": (0.62, 0.48, 0.34), "head": (0.42, 0.27, 0.16),
    "muzzle": (0.50, 0.34, 0.22), "ears": (0.26, 0.16, 0.09), "legs": (0.52, 0.38, 0.26),
    "tail": (0.44, 0.29, 0.18),
}
_BLACK = {
    "body": (0.12, 0.12, 0.13), "belly": (0.28, 0.28, 0.30), "head": (0.12, 0.12, 0.13),
    "muzzle": (0.18, 0.18, 0.20), "ears": (0.07, 0.07, 0.08), "legs": (0.20, 0.20, 0.22),
    "tail": (0.12, 0.12, 0.13),
}
_CREAM = {
    "body": (0.90, 0.84, 0.70), "belly": (0.96, 0.93, 0.84), "head": (0.90, 0.84, 0.70),
    "muzzle": (0.93, 0.88, 0.78), "ears": (0.74, 0.64, 0.50), "legs": (0.93, 0.88, 0.78),
    "tail": (0.92, 0.86, 0.74),
}

# Coat color keywords (NOT modifiers like "dark"/"light", which qualify regions).
_COATS = (
    (("golden", "gold", "yellow", "tan"), _GOLDEN),
    (("chocolate", "brown", "liver"), _BROWN),
    (("black", "ebony"), _BLACK),
    (("cream", "white", "ivory"), _CREAM),
)


def coat_palette(material: dict) -> dict:
    """Pick the coat from ``material.baseColor`` by the *earliest* color keyword.

    Region modifiers like "darker ears" / "cream chest" must not override the
    dominant coat, so we choose the palette whose keyword appears first in the
    string rather than first in table order.
    """
    text = str(material.get("baseColor", "golden")).lower()
    best_palette, best_pos = _GOLDEN, len(text) + 1
    for keywords, pal in _COATS:
        for k in keywords:
            pos = text.find(k)
            if 0 <= pos < best_pos:
                best_palette, best_pos = pal, pos
    return best_palette


def base_coat(material: dict) -> np.ndarray:
    return np.array(coat_palette(material)["body"], dtype=_F)


def region_color(material: dict, region: str) -> np.ndarray:
    pal = coat_palette(material)
    return np.array(pal.get(region, pal["body"]), dtype=_F)

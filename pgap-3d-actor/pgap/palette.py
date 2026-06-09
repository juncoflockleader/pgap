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
    "eyes": (0.05, 0.03, 0.02),    # dark eyes (near-black brown)
    "nose": (0.04, 0.03, 0.03),    # black nose
    "mouth": (0.10, 0.06, 0.05),   # dark mouth line
}
_BROWN = {
    "body": (0.40, 0.26, 0.15), "belly": (0.62, 0.48, 0.34), "head": (0.42, 0.27, 0.16),
    "muzzle": (0.50, 0.34, 0.22), "ears": (0.26, 0.16, 0.09), "legs": (0.52, 0.38, 0.26),
    "tail": (0.44, 0.29, 0.18), "eyes": (0.05, 0.03, 0.02),
    "nose": (0.04, 0.03, 0.03), "mouth": (0.10, 0.06, 0.05),
}
_BLACK = {
    "body": (0.12, 0.12, 0.13), "belly": (0.28, 0.28, 0.30), "head": (0.12, 0.12, 0.13),
    "muzzle": (0.18, 0.18, 0.20), "ears": (0.07, 0.07, 0.08), "legs": (0.20, 0.20, 0.22),
    "tail": (0.12, 0.12, 0.13), "eyes": (0.02, 0.02, 0.03),
    "nose": (0.03, 0.03, 0.04), "mouth": (0.05, 0.05, 0.06),
}
_CREAM = {
    "body": (0.90, 0.84, 0.70), "belly": (0.96, 0.93, 0.84), "head": (0.90, 0.84, 0.70),
    "muzzle": (0.93, 0.88, 0.78), "ears": (0.74, 0.64, 0.50), "legs": (0.93, 0.88, 0.78),
    "tail": (0.92, 0.86, 0.74), "eyes": (0.06, 0.04, 0.03),
    "nose": (0.10, 0.07, 0.06), "mouth": (0.14, 0.10, 0.08),
}
_STONE = {  # props: grey granite
    "body": (0.46, 0.46, 0.48), "belly": (0.40, 0.40, 0.42), "head": (0.46, 0.46, 0.48),
    "muzzle": (0.46, 0.46, 0.48), "ears": (0.38, 0.38, 0.40), "legs": (0.42, 0.42, 0.44),
    "tail": (0.46, 0.46, 0.48), "eyes": (0.10, 0.10, 0.11),
    "nose": (0.10, 0.10, 0.11), "mouth": (0.12, 0.12, 0.13),
}
_WOOD = {  # props: barrel wood
    "body": (0.45, 0.30, 0.16), "belly": (0.40, 0.27, 0.14), "head": (0.45, 0.30, 0.16),
    "muzzle": (0.45, 0.30, 0.16), "ears": (0.38, 0.25, 0.12), "legs": (0.42, 0.28, 0.15),
    "tail": (0.45, 0.30, 0.16), "eyes": (0.10, 0.07, 0.04),
    "nose": (0.08, 0.05, 0.03), "mouth": (0.12, 0.08, 0.05),
}

# The pupil is the darkest point of the eye on every coat (reuse the nose black).
for _coat_pal in (_GOLDEN, _BROWN, _BLACK, _CREAM, _STONE, _WOOD):
    _coat_pal["pupil"] = _coat_pal["nose"]

# Coat color keywords (NOT modifiers like "dark"/"light", which qualify regions).
_COATS = (
    (("golden", "gold", "yellow", "tan"), _GOLDEN),
    (("chocolate", "liver"), _BROWN),
    (("black", "ebony"), _BLACK),
    (("cream", "ivory"), _CREAM),
    (("stone", "granite", "grey", "gray", "rock"), _STONE),
    (("wood", "wooden", "oak", "barrel", "brown"), _WOOD),
)


COAT_KEYWORDS = tuple(k for kws, _ in _COATS for k in kws)  # public capability surface

# Iris colors for the eyes region (sRGB). When ``material.eyeColor`` names one of
# these, the eyeball renders that hue instead of the coat's default near-black eye
# — so a creature can have amber, green, or glowing-red eyes. Stylized solid iris;
# pupil/catchlight detail is a texture-side upgrade (roadmap 1).
_IRIS = {
    "amber": (0.62, 0.34, 0.04), "gold": (0.66, 0.48, 0.08), "golden": (0.66, 0.48, 0.08),
    "yellow": (0.74, 0.64, 0.10), "orange": (0.72, 0.32, 0.05),
    "green": (0.10, 0.42, 0.14), "emerald": (0.05, 0.45, 0.22), "lime": (0.40, 0.62, 0.10),
    "blue": (0.10, 0.26, 0.58), "cyan": (0.10, 0.50, 0.56), "teal": (0.06, 0.42, 0.42),
    "red": (0.56, 0.05, 0.05), "crimson": (0.50, 0.04, 0.09),
    "violet": (0.36, 0.10, 0.46), "purple": (0.30, 0.08, 0.40),
    "pink": (0.80, 0.40, 0.50), "white": (0.90, 0.90, 0.92), "black": (0.03, 0.02, 0.02),
}
IRIS_KEYWORDS = tuple(_IRIS)  # public capability surface


def eye_color(material: dict) -> np.ndarray:
    """The iris color for the eyes region. ``material.eyeColor`` selects an iris by
    the *earliest* keyword in the string; absent/unrecognized falls back to the
    coat's default dark eye (the prior behavior)."""
    text = str(material.get("eyeColor", "")).lower()
    best, best_pos = None, len(text) + 1
    for k, rgb in _IRIS.items():
        pos = text.find(k)
        if 0 <= pos < best_pos:
            best, best_pos = rgb, pos
    if best is not None:
        return np.array(best, dtype=_F)
    return np.array(coat_palette(material)["eyes"], dtype=_F)


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

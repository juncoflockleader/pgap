"""Portrait generator — stylized "monster girl" bust shots, module-composed.

Module graph per archetype: behind-layer (wings / ears / hair) -> face base with
outline -> archetype overlays (drip, muzzle, cap shading) -> shared face kit
(eyes, brows, mouth, blush, fang) -> seeded accessory. All proportions live in
512-space and scale with spec.size.
"""

from __future__ import annotations

import numpy as np

from .draw import bezier, blend, canvas, ellipse, hsv, polygon, stroke

ARCHETYPES = ["slime", "bat", "wolf", "human"]

_EYE_HUES = [0.98, 0.10, 0.35, 0.60, 0.78]

_BASE = {
    "slime": {"hue": 0.48, "sat": 0.55, "val": 0.85, "alpha": 0.93},
    "bat":   {"hue": 0.75, "sat": 0.45, "val": 0.75, "alpha": 1.0},
    "wolf":  {"hue": 0.58, "sat": 0.14, "val": 0.72, "alpha": 1.0},
    "human": {"hue": 0.07, "sat": 0.28, "val": 0.96, "alpha": 1.0},
}

_HAIR_HUES = [0.05, 0.62, 0.95, 0.13]


def render_portrait(spec, rng: np.random.Generator) -> np.ndarray:
    size = int(spec.size)
    s = size / 512.0
    img = canvas(size, size)

    def el(cx, cy, rx, ry, color, **kw):
        ellipse(img, cx * s, cy * s, rx * s, ry * s, color, **kw)

    def poly(pts, color, **kw):
        polygon(img, [(x * s, y * s) for x, y in pts], color, **kw)

    def st(pts, width, color, **kw):
        stroke(img, [(x * s, y * s) for x, y in pts], width * s, color, **kw)

    def bz(p0, p1, p2):
        return bezier(p0, p1, p2)

    base = _BASE[spec.archetype]
    hue = (base["hue"] + float(rng.uniform(-0.035, 0.035))) % 1.0
    eye_hue = float(rng.choice(_EYE_HUES))
    blush_a = float(rng.uniform(0.45, 0.7))
    tilt = float(rng.uniform(-10.0, 10.0))
    acc_roll = float(rng.random())
    hair_hue = float(rng.choice(_HAIR_HUES))

    skin = hsv(hue, base["sat"], base["val"], base["alpha"])
    dark = hsv(hue, min(base["sat"] + 0.15, 1.0), base["val"] * 0.42)
    ink = (0.10, 0.08, 0.13, 1.0)

    cx, cy, rx, ry = 256.0, 295.0, 150.0, 142.0
    fang = spec.archetype in ("bat", "wolf")

    # --- behind layer ----------------------------------------------------
    if spec.archetype == "bat":
        wing = hsv(hue, 0.55, 0.40)
        wing2 = hsv(hue, 0.60, 0.30)
        poly([(30, 350), (10, 150), (130, 230)], wing)
        poly([(482, 350), (502, 150), (382, 230)], wing)
        poly([(70, 370), (45, 215), (150, 285)], wing2)
        poly([(442, 370), (467, 215), (362, 285)], wing2)
        poly([(140 + tilt, 75), (196, 205), (108, 195)], dark)
        poly([(372 - tilt, 75), (404, 195), (316, 205)], dark)
        poly([(146 + tilt, 102), (182, 195), (126, 190)], (1.0, 0.62, 0.72, 0.9))
        poly([(366 - tilt, 102), (386, 190), (330, 195)], (1.0, 0.62, 0.72, 0.9))
    elif spec.archetype == "wolf":
        poly([(115 + tilt, 65), (185, 195), (75, 185)], dark)
        poly([(397 - tilt, 65), (437, 185), (327, 195)], dark)
        poly([(122 + tilt, 92), (168, 185), (98, 180)], (0.95, 0.72, 0.78, 0.95))
        poly([(390 - tilt, 92), (414, 180), (344, 185)], (0.95, 0.72, 0.78, 0.95))
    elif spec.archetype == "human":
        hair = hsv(hair_hue, 0.55, 0.45)
        el(256, 250, 168, 150, hair)
    elif spec.archetype == "slime":
        # gel drip rising off the head
        el(256, 150, 52, 95, skin)
        el(256, 78, 22, 36, skin)

    # --- face base --------------------------------------------------------
    el(cx, cy, rx + 7, ry + 7, dark)
    el(cx, cy, rx, ry, skin)

    if spec.archetype == "slime":
        el(195, 235, 32, 52, (1.0, 1.0, 1.0, 0.38), rot=0.5)
        el(310, 380, 26, 38, hsv(hue, 0.65, 0.62, 0.35), rot=-0.4)
    elif spec.archetype == "wolf":
        el(256, 362, 80, 54, hsv(hue, 0.06, 0.92))
        el(256, 342, 15, 11, ink)
    elif spec.archetype == "human":
        hair = hsv(hair_hue, 0.55, 0.45)
        band = hsv(0.99, 0.75, 0.85)
        poly([(106, 212), (406, 212), (398, 240), (114, 240)], band)
        poly([(118, 235), (170, 158), (210, 245)], hair)
        poly([(196, 168), (258, 148), (302, 242)], hair)
        poly([(290, 162), (348, 178), (332, 252)], hair)
        st(bz((250, 120), (290, 70), (330, 105)), 4.0, hair)
    else:
        el(256, 198, 140, 68, hsv(hue, 0.60, 0.50, 0.28))

    # --- shared face kit ----------------------------------------------------
    for side in (-1.0, 1.0):
        ex, ey = 256.0 + side * 66.0, 295.0
        el(ex, ey, 30, 36, (1.0, 1.0, 1.0, 1.0))
        el(ex, ey + 2, 20, 27, hsv(eye_hue, 0.75, 0.80))
        el(ex, ey + 6, 9, 14, ink)
        el(ex - 9, ey - 10, 8, 10, (1.0, 1.0, 1.0, 0.95))
        el(ex + 9, ey + 10, 4, 5, (1.0, 1.0, 1.0, 0.8))
        st(bz((ex - 30, ey - 20), (ex, ey - 42), (ex + 30, ey - 20)), 4.0, ink)
        st(bz((ex - 20, ey - 54), (ex, ey - 60), (ex + 18, ey - 52)), 3.0, dark)

    st(bz((226, 386), (256, 402), (286, 386)), 4.5, ink)
    if fang:
        poly([(268, 390), (276, 406), (284, 390)], (1.0, 1.0, 1.0, 1.0))
    el(148, 348, 24, 14, (1.0, 0.60, 0.70, blush_a))
    el(364, 348, 24, 14, (1.0, 0.60, 0.70, blush_a))

    # --- seeded accessory ---------------------------------------------------
    if acc_roll < 0.45:
        fx, fy = 150.0, 172.0
        for k in range(5):
            ang = k * 2.0 * np.pi / 5.0
            el(fx + 13 * np.cos(ang), fy + 13 * np.sin(ang), 9, 9, (1.0, 0.92, 0.96, 0.95))
        el(fx, fy, 7, 7, (1.0, 0.82, 0.30, 1.0))
    elif acc_roll < 0.80:
        sx, sy = 372.0, 150.0
        poly([(sx - 16, sy), (sx, sy - 5), (sx + 16, sy), (sx, sy + 5)], (1.0, 0.95, 0.6, 0.9))
        poly([(sx, sy - 16), (sx + 5, sy), (sx, sy + 16), (sx - 5, sy)], (1.0, 0.95, 0.6, 0.9))

    return img

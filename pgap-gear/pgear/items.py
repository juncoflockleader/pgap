"""Gear item recipes — each composes a complete piece from part primitives along
+Y (grip near the origin, business end up), tagging parts with palette material
slots (metal / grip / accent / wood). A builder per template; the registry maps a
name to it. Deterministic: geometry is a pure function of (scale, variant, mats).
"""

from __future__ import annotations

from typing import Dict

from .geom import MeshBuilder


# --------------------------------------------------------------------------- #
# shared part helpers
# --------------------------------------------------------------------------- #
def _grip(mb, mats, y0, y1, r=0.012):
    mb.prism(y0, y1, r, mats["grip"], sides=8)


def _pommel(mb, mats, y_top, r=0.018, variant="round"):
    if variant == "disc":
        mb.box(y_top - 0.012, y_top, r * 2.2, 0.012, mats["accent"])
    else:
        mb.prism(y_top - 0.03, y_top - 0.008, r, mats["accent"], sides=8)
        mb.prism(y_top - 0.03, y_top - 0.045, r * 0.8, mats["accent"], sides=8, rtop=0.0)


def _blade(mb, mats, y0, length, w, t, curve=0.0, leaf=False, mat=None):
    """A tapered blade up +Y ending in a point; optional gentle curve / leaf bulge."""
    mat = mat or mats["metal"]
    n = 6
    for i in range(n):
        a, b = i / n, (i + 1) / n
        ya, yb = y0 + a * length, y0 + b * length
        shape = (1.0 - 0.45 * a)
        if leaf:
            shape = (0.6 + 0.9 * (1 - abs(a - 0.4) / 0.6))    # bulge mid
        wa = w * (1.0 - 0.42 * a) * (1.15 if leaf else 1.0)
        wb = w * (1.0 - 0.42 * b) * (1.15 if leaf else 1.0)
        ta, tb = t * (1 - 0.4 * a), t * (1 - 0.4 * b)
        cxa, cxb = curve * (a ** 1.4) * length, curve * (b ** 1.4) * length
        if i == n - 1:
            mb.frustum(ya, yb, wa, ta, 0, 0, mat, cx=cxa)        # tip
        else:
            mb.frustum(ya, yb, wa, ta, wb, tb, mat, cx=(cxa + cxb) / 2)


def _haft(mb, mats, y0, y1, r=0.014):
    mb.prism(y0, y1, r, mats["wood"], sides=8)


# --------------------------------------------------------------------------- #
# templates: (mb, mats, scale, variant) -> sockets dict
# --------------------------------------------------------------------------- #
def sword(mb, mats, scale=1.0, variant="straight", two_handed=False):
    grip = 0.16 * scale * (1.7 if two_handed else 1.0)
    guard_w = 0.20 * scale
    blade_len = (1.0 if not two_handed else 1.45) * scale - grip - 0.03
    _pommel(mb, mats, -grip)
    _grip(mb, mats, -grip, 0.0, r=0.012 * scale)
    mb.box(0.0, 0.03 * scale, guard_w, 0.03 * scale, mats["accent"])      # crossguard
    curve = {"curved": 0.16, "straight": 0.0, "leaf": 0.0}.get(variant, 0.0)
    _blade(mb, mats, 0.03 * scale, blade_len, 0.05 * scale, 0.012 * scale,
           curve=curve, leaf=(variant == "leaf"))
    return {"grip": -grip * 0.5}


def greatsword(mb, mats, scale=1.0, variant="straight"):
    return sword(mb, mats, scale=scale * 1.5, variant=variant, two_handed=True)


def dagger(mb, mats, scale=1.0, variant="straight"):
    return sword(mb, mats, scale=scale * 0.38, variant=variant)


def axe(mb, mats, scale=1.0, variant="battle"):
    haft = 0.8 * scale
    _grip(mb, mats, -haft, -haft + 0.12 * scale, r=0.012 * scale)
    _haft(mb, mats, -haft + 0.12 * scale, 0.04 * scale, r=0.013 * scale)
    # axe head: a wedge fanning out on +X near the top
    top = 0.0
    hw = 0.16 * scale
    mb.frustum(top - 0.06 * scale, top + 0.06 * scale, 0.03 * scale, 0.10 * scale,
               0.03 * scale, 0.02 * scale, mats["metal"], cx=hw * 0.6)
    mb.box(top - 0.05 * scale, top + 0.05 * scale, 0.04 * scale, 0.05 * scale,
           mats["metal"], cx=0.0)                                          # eye/socket
    if variant == "double":
        mb.frustum(top - 0.06 * scale, top + 0.06 * scale, 0.03 * scale, 0.10 * scale,
                   0.03 * scale, 0.02 * scale, mats["metal"], cx=-hw * 0.6)
    return {"grip": -haft + 0.06 * scale}


def spear(mb, mats, scale=1.0, variant="leaf"):
    shaft = 2.0 * scale
    _haft(mb, mats, -shaft, shaft * 0.06, r=0.013 * scale)
    _blade(mb, mats, shaft * 0.06, 0.26 * scale, 0.05 * scale, 0.014 * scale,
           leaf=(variant != "pike"))
    return {"grip": -shaft * 0.35}


def mace(mb, mats, scale=1.0, variant="flanged"):
    haft = 0.6 * scale
    _grip(mb, mats, -haft, -haft + 0.14 * scale, r=0.013 * scale)
    _haft(mb, mats, -haft + 0.14 * scale, 0.0, r=0.013 * scale)
    head_r = 0.05 * scale
    mb.prism(0.0, 0.10 * scale, head_r, mats["metal"], sides=8, rtop=head_r * 0.6)  # head
    if variant == "flanged":                                              # flanges
        for k in range(4):
            cx = head_r * (1 if k % 2 == 0 else -1) * 0.9
            cz = head_r * (1 if k < 2 else -1) * 0.9
            mb.box(0.02 * scale, 0.085 * scale, 0.02 * scale, 0.02 * scale,
                   mats["metal"], cx=cx, cz=cz)
    return {"grip": -haft + 0.07 * scale}


def staff(mb, mats, scale=1.0, variant="gem"):
    shaft = 1.8 * scale
    _haft(mb, mats, -shaft, 0.0, r=0.012 * scale)
    if variant == "gem":
        mb.prism(0.0, 0.05 * scale, 0.02 * scale, mats["accent"], sides=6)
        mb.prism(0.04 * scale, 0.10 * scale, 0.03 * scale, "gem_blue", sides=6, rtop=0.0)
    else:
        mb.prism(0.0, 0.10 * scale, 0.022 * scale, mats["accent"], sides=8, rtop=0.0)
    return {"grip": -shaft * 0.4}


def bow(mb, mats, scale=1.0, variant="recurve"):
    half = 0.6 * scale
    _grip(mb, mats, -0.08 * scale, 0.08 * scale, r=0.014 * scale)
    for sign in (1.0, -1.0):                       # two limbs curving back (+Z)
        n = 5
        for i in range(n):
            a, b = i / n, (i + 1) / n
            ya, yb = sign * (0.08 + a * half) * scale, sign * (0.08 + b * half) * scale
            za, zb = -(a ** 2) * 0.18 * scale, -(b ** 2) * 0.18 * scale
            mb.frustum(min(ya, yb), max(ya, yb), 0.016 * scale, 0.016 * scale,
                       0.012 * scale, 0.012 * scale, mats["wood"], cz=(za + zb) / 2)
    # string (thin, straight)
    mb.box(-half * scale, half * scale, 0.004 * scale, 0.004 * scale, "bone", cz=-0.02 * scale)
    return {"grip": 0.0}


def shield(mb, mats, scale=1.0, variant="round"):
    if variant == "kite" or variant == "heater":
        mb.frustum(-0.45 * scale, 0.10 * scale, 0.40 * scale, 0.05 * scale,
                   0.30 * scale, 0.05 * scale, mats["wood"])
        mb.frustum(0.10 * scale, 0.45 * scale, 0.30 * scale, 0.05 * scale,
                   0.0, 0.0, mats["wood"])                                # pointed bottom up
    else:                                                                  # round
        mb.prism(-0.03 * scale, 0.03 * scale, 0.42 * scale, mats["wood"], sides=16)
    mb.prism(0.03 * scale, 0.08 * scale, 0.07 * scale, mats["metal"], sides=12, rtop=0.04 * scale)  # boss
    return {"grip": -0.04 * scale}

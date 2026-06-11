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


def _blade(mb, mats, y0, length, w, t, curve=0.0, leaf=False, mat=None, cx=0.0):
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
        cxa = cx + curve * (a ** 1.4) * length
        cxb = cx + curve * (b ** 1.4) * length
        if i == n - 1:
            mb.frustum(ya, yb, wa, ta, 0, 0, mat, cx=cxa, cx1=cxb)        # tip
        else:
            mb.frustum(ya, yb, wa, ta, wb, tb, mat, cx=cxa, cx1=cxb)


def _haft(mb, mats, y0, y1, r=0.014):
    mb.prism(y0, y1, r, mats["wood"], sides=8)


def _crossguard(mb, mats, y, w, scale=1.0):
    mb.box(y - 0.012 * scale, y + 0.012 * scale, w, 0.025 * scale, mats["accent"])


def _spike(mb, mat, y0, y1, r, cx=0.0, cz=0.0, sides=4):
    mb.prism(y0, y1, r, mat, sides=sides, cx=cx, cz=cz, rtop=0.0)


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


def katana(mb, mats, scale=1.0, variant="uchigatana"):
    grip_mult = {"wakizashi": 0.72, "great": 1.35, "nodachi": 1.45}.get(variant, 1.0)
    blade_mult = {"wakizashi": 0.56, "great": 1.32, "nodachi": 1.42}.get(variant, 1.0)
    grip = 0.22 * scale * grip_mult
    _pommel(mb, mats, -grip, r=0.014 * scale, variant="disc")
    _grip(mb, mats, -grip, 0.0, r=0.010 * scale)
    mb.prism(-0.006 * scale, 0.012 * scale, 0.042 * scale, mats["accent"], sides=16)
    _blade(mb, mats, 0.012 * scale, 0.88 * scale * blade_mult, 0.038 * scale,
           0.009 * scale, curve=0.11 if variant != "wakizashi" else 0.07)
    return {"grip": -grip * 0.48}


def thrusting_sword(mb, mats, scale=1.0, variant="rapier"):
    heavy = variant in ("heavy", "great_epee", "stitcher")
    grip = (0.15 if not heavy else 0.20) * scale
    blade_len = (0.78 if not heavy else 1.05) * scale
    blade_w = (0.018 if variant == "rapier" else 0.026 if not heavy else 0.036) * scale
    _pommel(mb, mats, -grip, r=0.014 * scale, variant="disc")
    _grip(mb, mats, -grip, 0.0, r=0.010 * scale)
    mb.prism(-0.005 * scale, 0.020 * scale, 0.060 * scale, mats["accent"], sides=16)
    _crossguard(mb, mats, 0.010 * scale, 0.16 * scale if not heavy else 0.20 * scale, scale)
    _blade(mb, mats, 0.020 * scale, blade_len, blade_w, 0.010 * scale)
    return {"grip": -grip * 0.5}


def twinblade(mb, mats, scale=1.0, variant="balanced"):
    grip = 0.28 * scale
    blade_len = (0.46 if variant != "peeler" else 0.58) * scale
    blade_w = (0.040 if variant != "peeler" else 0.050) * scale
    _grip(mb, mats, -grip * 0.5, grip * 0.5, r=0.012 * scale)
    _crossguard(mb, mats, grip * 0.5, 0.15 * scale, scale)
    _crossguard(mb, mats, -grip * 0.5, 0.15 * scale, scale)
    _blade(mb, mats, grip * 0.5 + 0.010 * scale, blade_len, blade_w, 0.010 * scale,
           leaf=(variant == "leaf"))
    _blade(mb, mats, -grip * 0.5 - 0.010 * scale, -blade_len, blade_w, 0.010 * scale,
           leaf=(variant == "leaf"))
    if variant == "ornate":
        mb.prism(-0.030 * scale, 0.030 * scale, 0.030 * scale, mats["accent"], sides=8)
    return {"grip": 0.0}


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
    elif variant == "crescent":
        mb.frustum(top - 0.08 * scale, top + 0.08 * scale, 0.03 * scale, 0.13 * scale,
                   0.02 * scale, 0.01 * scale, mats["metal"], cx=-hw * 0.45)
    elif variant == "cleaver":
        mb.box(top - 0.10 * scale, top + 0.06 * scale, 0.11 * scale, 0.035 * scale,
               mats["metal"], cx=hw * 0.55)
    return {"grip": -haft + 0.06 * scale}


def hammer(mb, mats, scale=1.0, variant="warhammer"):
    haft = (0.68 if variant != "great" else 0.95) * scale
    _grip(mb, mats, -haft, -haft + 0.16 * scale, r=0.013 * scale)
    _haft(mb, mats, -haft + 0.16 * scale, 0.0, r=0.014 * scale)
    if variant == "club":
        mb.prism(0.0, 0.18 * scale, 0.050 * scale, mats["wood"], sides=8, rtop=0.035 * scale)
    elif variant == "pick":
        mb.box(0.0, 0.08 * scale, 0.20 * scale, 0.025 * scale, mats["metal"])
        _spike(mb, mats["metal"], 0.03 * scale, 0.14 * scale, 0.025 * scale, cx=0.10 * scale)
    else:
        head_w = (0.18 if variant != "great" else 0.26) * scale
        mb.box(-0.02 * scale, 0.10 * scale, head_w, 0.060 * scale, mats["metal"])
        if variant == "spiked":
            for cx in (-0.08 * scale, 0.08 * scale):
                _spike(mb, mats["metal"], 0.02 * scale, 0.12 * scale, 0.016 * scale, cx=cx)
    return {"grip": -haft + 0.08 * scale}


def spear(mb, mats, scale=1.0, variant="leaf"):
    shaft = 2.0 * scale
    _haft(mb, mats, -shaft, shaft * 0.06, r=0.013 * scale)
    _blade(mb, mats, shaft * 0.06, 0.26 * scale, 0.05 * scale, 0.014 * scale,
           leaf=(variant != "pike"))
    return {"grip": -shaft * 0.35}


def halberd(mb, mats, scale=1.0, variant="axe"):
    shaft = 1.75 * scale
    _haft(mb, mats, -shaft, 0.12 * scale, r=0.014 * scale)
    _grip(mb, mats, -shaft, -shaft + 0.22 * scale, r=0.013 * scale)
    if variant == "glaive":
        _blade(mb, mats, 0.02 * scale, 0.48 * scale, 0.060 * scale, 0.014 * scale,
               curve=0.14)
    else:
        _blade(mb, mats, 0.10 * scale, 0.28 * scale, 0.044 * scale, 0.013 * scale)
        mb.frustum(-0.02 * scale, 0.14 * scale, 0.035 * scale, 0.11 * scale,
                   0.020 * scale, 0.025 * scale, mats["metal"], cx=0.11 * scale)
        if variant in ("bill", "crescent"):
            mb.frustum(0.00 * scale, 0.16 * scale, 0.025 * scale, 0.08 * scale,
                       0.010 * scale, 0.010 * scale, mats["metal"], cx=-0.10 * scale)
    if variant == "banner":
        mb.box(-0.08 * scale, 0.16 * scale, 0.020 * scale, 0.18 * scale,
               mats["accent"], cx=-0.075 * scale)
    return {"grip": -shaft * 0.42}


def reaper(mb, mats, scale=1.0, variant="scythe"):
    shaft = 1.65 * scale
    _haft(mb, mats, -shaft, 0.10 * scale, r=0.013 * scale)
    _grip(mb, mats, -shaft, -shaft + 0.20 * scale, r=0.013 * scale)
    blade_mat = "obsidian" if variant == "grave" else mats["metal"]
    _blade(mb, {**mats, "metal": blade_mat}, 0.00 * scale, 0.48 * scale,
           0.050 * scale, 0.012 * scale, curve=0.25, leaf=(variant == "winged"))
    mb.box(0.02 * scale, 0.18 * scale, 0.025 * scale, 0.035 * scale,
           mats["accent"], cx=-0.045 * scale)
    if variant == "halo":
        mb.prism(0.26 * scale, 0.30 * scale, 0.060 * scale, "holy", sides=16)
    return {"grip": -shaft * 0.42}


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


def flail(mb, mats, scale=1.0, variant="spiked"):
    haft = 0.56 * scale
    _grip(mb, mats, -haft, -haft + 0.14 * scale, r=0.013 * scale)
    _haft(mb, mats, -haft + 0.14 * scale, -0.04 * scale, r=0.013 * scale)
    for i in range(4):
        y = -0.02 * scale + i * 0.035 * scale
        mb.box(y, y + 0.020 * scale, 0.012 * scale, 0.012 * scale, mats["accent"],
               cx=(0.006 if i % 2 else -0.006) * scale)
    head_r = (0.046 if variant != "chainlink" else 0.055) * scale
    mb.prism(0.12 * scale, 0.22 * scale, head_r, mats["metal"], sides=8, rtop=head_r * 0.85)
    if variant in ("spiked", "chainlink"):
        for cx, cz in ((head_r, 0), (-head_r, 0), (0, head_r), (0, -head_r)):
            mb.box(0.155 * scale, 0.19 * scale, 0.018 * scale, 0.018 * scale,
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


def sacred_seal(mb, mats, scale=1.0, variant="finger"):
    grip = 0.16 * scale
    _grip(mb, mats, -grip, 0.0, r=0.011 * scale)
    if variant == "clawmark":
        mb.prism(0.0, 0.06 * scale, 0.042 * scale, mats["accent"], sides=6)
        for cx in (-0.030 * scale, 0.0, 0.030 * scale):
            _spike(mb, mats["metal"], 0.04 * scale, 0.16 * scale, 0.012 * scale, cx=cx, sides=4)
    elif variant == "spiral":
        for i, r in enumerate((0.026, 0.038, 0.050)):
            mb.prism((0.020 + i * 0.020) * scale, (0.034 + i * 0.020) * scale,
                     r * scale, mats["accent"], sides=12)
    else:
        mb.prism(0.0, 0.045 * scale, 0.055 * scale, mats["accent"], sides=16)
        mb.prism(0.040 * scale, 0.120 * scale, 0.026 * scale,
                 "holy" if variant == "order" else mats["metal"], sides=8, rtop=0.0)
    return {"grip": -grip * 0.45}


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


def greatbow(mb, mats, scale=1.0, variant="great"):
    sockets = bow(mb, mats, scale=scale * 1.35, variant="longbow")
    mb.box(-0.76 * scale, 0.76 * scale, 0.026 * scale, 0.030 * scale,
           mats["wood"], cx=0.035 * scale, cz=-0.035 * scale)
    mb.box(-0.09 * scale, 0.09 * scale, 0.048 * scale, 0.018 * scale,
           mats["accent"], cz=-0.020 * scale)
    if variant == "golem":
        for y in (-0.72 * scale, 0.72 * scale):
            mb.prism(y - 0.040 * scale, y + 0.040 * scale, 0.032 * scale,
                     mats["metal"], sides=8)
    elif variant == "horn":
        for y in (-0.75 * scale, 0.75 * scale):
            _spike(mb, "bone", y, y + (0.10 if y > 0 else -0.10) * scale,
                   0.025 * scale, sides=6)
    return sockets


def crossbow(mb, mats, scale=1.0, variant="light"):
    stock = (0.62 if variant != "heavy" else 0.82) * scale
    _haft(mb, mats, -stock * 0.55, stock * 0.45, r=0.014 * scale)
    mb.box(-0.12 * scale, 0.02 * scale, 0.050 * scale, 0.075 * scale, mats["grip"],
           cz=-0.035 * scale)
    limb_w = (0.58 if variant != "heavy" else 0.78) * scale
    mb.box(0.16 * scale, 0.22 * scale, limb_w, 0.018 * scale, mats["wood"],
           cz=-0.020 * scale)
    mb.box(0.17 * scale, 0.19 * scale, limb_w * 0.90, 0.004 * scale, "bone",
           cz=-0.060 * scale)
    if variant in ("repeating", "pulley"):
        mb.box(0.02 * scale, 0.14 * scale, 0.070 * scale, 0.050 * scale, mats["accent"],
               cz=0.030 * scale)
    _blade(mb, mats, 0.18 * scale, 0.30 * scale, 0.018 * scale, 0.008 * scale)
    return {"grip": -0.05 * scale}


def torch(mb, mats, scale=1.0, variant="flame"):
    shaft = 0.70 * scale
    _grip(mb, mats, -shaft, -shaft + 0.18 * scale, r=0.014 * scale)
    _haft(mb, mats, -shaft + 0.18 * scale, 0.04 * scale, r=0.013 * scale)
    mb.prism(0.02 * scale, 0.10 * scale, 0.042 * scale, mats["accent"], sides=8)
    flame_mat = "ghostflame" if variant == "ghostflame" else "holy" if variant == "sentry" else "flame"
    mb.prism(0.09 * scale, 0.26 * scale, 0.050 * scale, flame_mat, sides=8, rtop=0.0)
    if variant == "wire":
        mb.box(0.02 * scale, 0.13 * scale, 0.11 * scale, 0.012 * scale, mats["metal"])
    return {"grip": -shaft + 0.09 * scale}


def claw(mb, mats, scale=1.0, variant="hook"):
    grip = 0.18 * scale
    _grip(mb, mats, -grip, 0.0, r=0.014 * scale)
    mb.box(-0.02 * scale, 0.08 * scale, 0.15 * scale, 0.045 * scale, mats["accent"])
    blade_len = (0.34 if variant != "beast" else 0.44) * scale
    curve = 0.18 if variant in ("hook", "beast") else 0.08
    for cx in (-0.045 * scale, 0.0, 0.045 * scale):
        _blade(mb, mats, 0.06 * scale, blade_len, 0.016 * scale, 0.006 * scale,
               curve=curve, mat=mats["metal"], cx=cx)
        mb.box(0.02 * scale, 0.07 * scale, 0.018 * scale, 0.020 * scale,
               mats["accent"], cx=cx)
    return {"grip": -grip * 0.5}


def fist(mb, mats, scale=1.0, variant="caestus"):
    grip = 0.16 * scale
    _grip(mb, mats, -grip, 0.02 * scale, r=0.015 * scale)
    mb.box(-0.04 * scale, 0.08 * scale, 0.16 * scale, 0.055 * scale, mats["grip"])
    for cx in (-0.055 * scale, -0.018 * scale, 0.018 * scale, 0.055 * scale):
        mb.box(0.04 * scale, 0.10 * scale, 0.026 * scale, 0.026 * scale,
               mats["metal"], cx=cx, cz=0.020 * scale)
        if variant == "spiked":
            _spike(mb, mats["metal"], 0.09 * scale, 0.17 * scale, 0.010 * scale,
                   cx=cx, cz=0.020 * scale, sides=4)
    if variant == "katar":
        _blade(mb, mats, 0.08 * scale, 0.36 * scale, 0.030 * scale, 0.008 * scale)
    return {"grip": -grip * 0.5}


def perfume_bottle(mb, mats, scale=1.0, variant="round"):
    grip = 0.11 * scale
    _grip(mb, mats, -grip, 0.0, r=0.010 * scale)
    body_sides = 12 if variant == "round" else 6
    mb.prism(0.00 * scale, 0.12 * scale, 0.055 * scale, "crystal", sides=body_sides,
             rtop=0.040 * scale)
    mb.prism(0.10 * scale, 0.17 * scale, 0.022 * scale, mats["accent"], sides=8)
    vapor = {"fire": "flame", "lightning": "holy", "poison": "gem_red"}.get(variant, "ghostflame")
    mb.prism(0.16 * scale, 0.24 * scale, 0.030 * scale, vapor, sides=8, rtop=0.0)
    return {"grip": -grip * 0.45}


def shield(mb, mats, scale=1.0, variant="round"):
    if variant == "tower":
        mb.box(-0.58 * scale, 0.42 * scale, 0.48 * scale, 0.060 * scale, mats["wood"])
        mb.box(-0.55 * scale, 0.38 * scale, 0.060 * scale, 0.075 * scale, mats["accent"],
               cx=-0.22 * scale)
        mb.box(-0.55 * scale, 0.38 * scale, 0.060 * scale, 0.075 * scale, mats["accent"],
               cx=0.22 * scale)
    elif variant == "palisade":
        for cx in (-0.18 * scale, -0.06 * scale, 0.06 * scale, 0.18 * scale):
            mb.box(-0.55 * scale, 0.36 * scale, 0.090 * scale, 0.060 * scale,
                   mats["wood"], cx=cx)
            _spike(mb, mats["metal"], 0.34 * scale, 0.48 * scale, 0.030 * scale, cx=cx)
    elif variant == "thrusting":
        mb.box(-0.34 * scale, 0.28 * scale, 0.34 * scale, 0.060 * scale, mats["wood"])
        _blade(mb, mats, 0.20 * scale, 0.44 * scale, 0.050 * scale, 0.020 * scale)
    elif variant == "kite" or variant == "heater" or variant == "great":
        s = 1.20 if variant == "great" else 1.0
        mb.frustum(-0.45 * scale, 0.10 * scale, 0.40 * scale, 0.05 * scale,
                   0.30 * scale * s, 0.05 * scale, mats["wood"])
        mb.frustum(0.10 * scale, 0.45 * scale, 0.30 * scale, 0.05 * scale,
                   0.0, 0.0, mats["wood"])                                # pointed bottom up
    else:                                                                  # round / buckler
        r = 0.28 * scale if variant == "buckler" else 0.42 * scale
        mb.prism(-0.03 * scale, 0.03 * scale, r, mats["wood"], sides=16)
    mb.prism(0.03 * scale, 0.08 * scale, 0.07 * scale, mats["metal"], sides=12, rtop=0.04 * scale)  # boss
    if variant in ("buckler", "round", "great"):
        mb.prism(0.00 * scale, 0.018 * scale, (0.31 if variant == "buckler" else 0.46) * scale,
                 mats["accent"], sides=16)
    return {"grip": -0.04 * scale}

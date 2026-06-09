"""Prop proxy archetypes — a prop kind → a list of box parts (real-world metres,
Y-up, base at y0=0) for ``gltf.prop_gltf``. Stylised low-poly proxies (a lamp is a
pole + a glowing head, a tree is a trunk + a canopy, a sign is an emissive panel),
not detailed models — enough to read the street furniture of each cell.
"""

from __future__ import annotations


def _post(h, head=(40, 40, 46), emissive=None):
    return [
        {"cx": 0, "cz": 0, "y0": 0, "sx": 0.18, "sz": 0.18, "sy": h, "color": (64, 64, 70)},
        {"cx": 0, "cz": 0, "y0": h - 0.4, "sx": 0.5, "sz": 0.35, "sy": 0.4,
         "color": head, "emissive": emissive},
    ]


def _tree():
    return [
        {"cx": 0, "cz": 0, "y0": 0, "sx": 0.3, "sz": 0.3, "sy": 2.0, "color": (94, 64, 42)},
        {"cx": 0, "cz": 0, "y0": 1.6, "sx": 2.4, "sz": 2.4, "sy": 2.6, "color": (72, 118, 56)},
    ]


def _car(color=(70, 90, 120)):
    return [
        {"cx": 0, "cz": 0, "y0": 0.25, "sx": 4.2, "sz": 1.8, "sy": 0.85, "color": color},
        {"cx": -0.2, "cz": 0, "y0": 1.05, "sx": 2.2, "sz": 1.65, "sy": 0.6,
         "color": tuple(int(x * 0.7) for x in color)},
    ]


def _sign(color, wide=False):
    return [
        {"cx": 0, "cz": 0, "y0": 0, "sx": 0.16, "sz": 0.16, "sy": 3.0, "color": (48, 48, 54)},
        {"cx": 0, "cz": 0, "y0": 2.6, "sx": 0.18, "sz": (2.6 if wide else 1.6), "sy": 2.2,
         "color": (28, 28, 34), "emissive": color},
    ]


def _box(w, d, h, color, y0=0.0, emissive=None):
    return [{"cx": 0, "cz": 0, "y0": y0, "sx": w, "sz": d, "sy": h,
             "color": color, "emissive": emissive}]


def prop_parts(kind: str, fstyle: dict) -> list:
    """Box parts for a prop ``kind``, accenting with the cell's emissive when lit.
    Unknown kinds fall back to a neutral marker box."""
    acc = fstyle.get("emissive") or (255, 180, 90)
    table = {
        "traffic_light": _post(5.5, head=(30, 30, 34), emissive=(230, 60, 40)),
        "lamp_post": _post(5.0, head=(255, 240, 205), emissive=(255, 225, 160)),
        "gas_lamp": _post(3.4, head=(255, 210, 140), emissive=(255, 180, 90)),
        "power_pole": _post(7.5, head=(70, 70, 76)),
        "airship_mast": _post(10.0, head=(120, 100, 70)),
        "lamp": _post(5.0, head=(255, 240, 205), emissive=(255, 225, 160)),
        "street_tree": _tree(),
        "sedan": _car((70, 90, 120)),
        "kei_car": _car((210, 210, 215)),
        "neon_sign": _sign(acc),
        "vertical_sign": _sign((255, 80, 160)),
        "holo_billboard": _sign((80, 200, 255), wide=True),
        "banner": _box(0.15, 2.0, 2.5, (160, 40, 50), y0=3.0),
        "vending_machine": _box(1.0, 0.7, 1.9, (40, 120, 160), emissive=(120, 200, 230)),
        "parking": _box(2.5, 5.0, 0.06, (60, 60, 66)),
        "steam_vent": _box(0.8, 0.8, 0.6, (80, 70, 60)),
        "pipe_run": _box(0.4, 3.0, 0.4, (120, 90, 55)),
    }
    return table.get(kind, _box(0.8, 0.8, 1.4, (120, 120, 128)))

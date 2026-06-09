"""Style profiles — the (era, culture) knob tables that drive every generator.

v1 cells (PRD.md §6): the profile selects street network, block/lot scale, height
distribution, roof/silhouette, materials/palette, and signature props. Geometry
itself is assembled by the building module engine (C1+); this table is the source
of truth for *how* a cell looks.
"""

from __future__ import annotations

from typing import Dict, Tuple

# (era, culture) -> profile
STYLE_PROFILES: Dict[Tuple[str, str], dict] = {
    ("modern", "american"): {
        "streetNet": "grid",
        "blockSizeM": 120.0,
        "streetWidthM": 20.0,
        "lotsPerBlock": [2, 2],
        "floors": [1, 6],           # storefronts -> mid-rise
        "floorHeightM": 4.0,
        "roof": "flat",
        "materials": ["concrete", "brick", "glass"],
        "palette": "muted grey-brown",
        "props": ["traffic_light", "sedan", "street_tree", "lamp_post", "parking"],
        "density": 0.7,
        "facade": {
            "wall": (172, 161, 148), "trim": (92, 86, 78), "glass": (122, 150, 170),
            "roof": (96, 96, 102), "bay_m": 4.5, "arch": False,
            "ground": "storefront", "emissive": None, "lit_frac": 0.0,
        },
    },
    ("modern", "japan"): {
        "streetNet": "fine_grid",
        "blockSizeM": 70.0,
        "streetWidthM": 9.0,
        "lotsPerBlock": [3, 3],
        "floors": [2, 9],
        "floorHeightM": 3.4,
        "roof": "flat_utilitarian",
        "materials": ["white_panel", "grey_panel", "glass"],
        "palette": "white-grey + neon signage",
        "props": ["vending_machine", "power_pole", "kei_car", "vertical_sign", "banner"],
        "density": 0.9,
        "facade": {
            "wall": (216, 218, 222), "trim": (138, 143, 150), "glass": (150, 176, 192),
            "roof": (112, 114, 120), "bay_m": 3.2, "arch": False,
            "ground": "storefront", "emissive": (255, 90, 140), "lit_frac": 0.18,
        },
    },
    ("futuristic", "cyberpunk"): {
        "streetNet": "organic",
        "blockSizeM": 90.0,
        "streetWidthM": 14.0,
        "lotsPerBlock": [2, 2],
        "floors": [6, 40],          # megablocks
        "floorHeightM": 4.5,
        "roof": "antenna_setback",
        "materials": ["dark_concrete", "glass", "neon_emissive"],
        "palette": "dark + saturated neon",
        "props": ["neon_sign", "holo_billboard", "drone", "skyway", "vapor"],
        "density": 0.95,
        "facade": {
            "wall": (40, 42, 54), "trim": (24, 25, 32), "glass": (22, 26, 44),
            "roof": (28, 28, 38), "bay_m": 3.6, "arch": False,
            "ground": "storefront", "emissive": (60, 200, 255), "lit_frac": 0.55,
        },
    },
    ("futuristic", "steampunk"): {
        "streetNet": "curved_industrial",
        "blockSizeM": 110.0,
        "streetWidthM": 16.0,
        "lotsPerBlock": [2, 2],
        "floors": [2, 12],
        "floorHeightM": 4.2,
        "roof": "dome_smokestack",
        "materials": ["brass", "copper", "iron", "soot_brick"],
        "palette": "brass-bronze-soot, warm",
        "props": ["gas_lamp", "airship_mast", "steam_vent", "pipe_run", "dirigible"],
        "density": 0.6,
        "facade": {
            "wall": (104, 70, 56), "trim": (168, 128, 62), "glass": (150, 138, 104),
            "roof": (150, 110, 70), "bay_m": 4.0, "arch": True,
            "ground": "arch", "emissive": (255, 178, 92), "lit_frac": 0.22,
        },
    },
}

# Sensible facade defaults for any profile that omits one (keeps facade.py simple).
_FACADE_DEFAULT = {
    "wall": (160, 160, 165), "trim": (90, 90, 95), "glass": (130, 150, 165),
    "roof": (95, 95, 100), "bay_m": 4.0, "arch": False,
    "ground": "storefront", "emissive": None, "lit_frac": 0.0,
}


def facade_for(profile: dict) -> dict:
    """The facade skin spec for a profile (wall/trim/glass/roof colors, window
    rhythm, ground-floor style, optional emissive lit windows)."""
    return {**_FACADE_DEFAULT, **profile.get("facade", {})}

# Building module kinds the kit assembler (C1+) composes per profile.
MODULE_KINDS = ("foundation", "floor", "roof", "door", "window", "balcony", "ornament")


def profile_for(era: str, culture: str) -> dict:
    return STYLE_PROFILES[(era, culture)]

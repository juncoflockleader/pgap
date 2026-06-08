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
    },
}

# Building module kinds the kit assembler (C1+) composes per profile.
MODULE_KINDS = ("foundation", "floor", "roof", "door", "window", "balcony", "ornament")


def profile_for(era: str, culture: str) -> dict:
    return STYLE_PROFILES[(era, culture)]

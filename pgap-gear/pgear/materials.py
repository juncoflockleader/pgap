"""Gear material library — PBR factors per named material (no textures needed for
hard-edged gear; flat per-part materials read cleanly). sRGB baseColor 0..1."""

from __future__ import annotations

from typing import Dict

# name -> (baseColor rgb 0..1, metallic, roughness)
MATERIALS: Dict[str, tuple] = {
    "steel": ((0.74, 0.76, 0.80), 1.0, 0.28),
    "dark_steel": ((0.18, 0.19, 0.22), 1.0, 0.34),
    "iron": ((0.42, 0.43, 0.46), 1.0, 0.45),
    "bronze": ((0.62, 0.43, 0.22), 1.0, 0.36),
    "verdigris": ((0.26, 0.48, 0.42), 1.0, 0.42),
    "gold": ((0.86, 0.69, 0.27), 1.0, 0.22),
    "silver": ((0.84, 0.85, 0.88), 1.0, 0.20),
    "obsidian": ((0.07, 0.07, 0.10), 0.3, 0.18),
    "wood": ((0.40, 0.27, 0.15), 0.0, 0.75),
    "dark_wood": ((0.24, 0.16, 0.10), 0.0, 0.70),
    "leather": ((0.32, 0.20, 0.12), 0.0, 0.80),
    "leather_black": ((0.10, 0.09, 0.09), 0.0, 0.70),
    "bone": ((0.86, 0.82, 0.70), 0.0, 0.65),
    "cloth": ((0.45, 0.20, 0.22), 0.0, 0.90),
    "crystal": ((0.45, 0.72, 0.95), 0.0, 0.12),
    "gem_blue": ((0.15, 0.35, 0.85), 0.0, 0.10),
    "gem_red": ((0.80, 0.10, 0.16), 0.0, 0.10),
    "flame": ((1.00, 0.34, 0.08), 0.0, 0.18),
    "ghostflame": ((0.38, 0.82, 0.92), 0.0, 0.10),
    "holy": ((0.95, 0.82, 0.38), 0.0, 0.16),
}

# coarse "blade/metal" keyword -> material
_METAL_KW = {
    "steel": "steel", "iron": "iron", "bronze": "bronze", "brass": "bronze",
    "gold": "gold", "golden": "gold", "silver": "silver", "obsidian": "obsidian",
    "glass": "obsidian", "bone": "bone", "black steel": "dark_steel",
    "black iron": "dark_steel", "dark": "dark_steel", "meteor": "dark_steel",
    "meteoric": "dark_steel", "crystal": "crystal", "glintstone": "crystal",
    "verdigris": "verdigris",
}
_GRIP_KW = {"leather": "leather", "black leather": "leather_black", "wood": "wood",
            "wooden": "wood", "wire": "silver", "cloth": "cloth", "wrapped": "leather"}
_ACCENT_KW = {"gold": "gold", "golden": "gold", "brass": "bronze", "bronze": "bronze",
              "silver": "silver", "ruby": "gem_red", "sapphire": "gem_blue",
              "red": "gem_red", "blood": "gem_red", "crystal": "crystal",
              "glintstone": "crystal", "blue": "gem_blue", "flame": "flame",
              "fire": "flame", "ghostflame": "ghostflame", "ghost": "ghostflame",
              "holy": "holy", "sacred": "holy"}


def factors(name: str) -> dict:
    rgb, metal, rough = MATERIALS.get(name, MATERIALS["iron"])
    return {"baseColorFactor": [round(rgb[0], 4), round(rgb[1], 4), round(rgb[2], 4), 1.0],
            "metallicFactor": float(metal), "roughnessFactor": float(rough)}


def pick(text: str, table: dict, default: str) -> str:
    """First keyword in ``text`` (by position) whose value names a material."""
    best, pos, kw_len = default, len(text) + 1, -1
    for kw, mat in table.items():
        i = text.find(kw)
        if 0 <= i and (i < pos or (i == pos and len(kw) > kw_len)):
            best, pos, kw_len = mat, i, len(kw)
    return best


def resolve_materials(text: str, base_metal: str, base_grip: str,
                      base_accent: str, base_wood: str = "wood") -> dict:
    """Map a freeform material string to the (metal, grip, accent) palette."""
    t = (text or "").lower()
    return {
        "metal": pick(t, _METAL_KW, base_metal),
        "grip": pick(t, _GRIP_KW, base_grip),
        "accent": pick(t, _ACCENT_KW, base_accent),
        "wood": pick(t, {"dark wood": "dark_wood", "wood": "wood", "oak": "wood",
                         "ash": "wood", "ebony": "dark_wood"}, base_wood),
    }

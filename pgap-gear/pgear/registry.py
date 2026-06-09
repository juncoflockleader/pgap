"""Gear template registry — the vocabulary an LLM/human composes from.

Maps a template name to its builder, allowed variants, default size, category, and
the base material palette (metal / grip / accent / wood slots). The grammar
validator, capability report, and NL front-end all read this.
"""

from __future__ import annotations

from typing import Dict

from . import items

# name -> {fn, variants, scale, category, mats}
TEMPLATES: Dict[str, dict] = {
    "sword": {"fn": items.sword, "variants": ["straight", "curved", "leaf"], "scale": 1.0,
              "category": "weapon",
              "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "wood"}},
    "greatsword": {"fn": items.greatsword, "variants": ["straight", "curved"], "scale": 1.0,
                   "category": "weapon",
                   "mats": {"metal": "steel", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "dagger": {"fn": items.dagger, "variants": ["straight", "curved", "leaf"], "scale": 1.0,
               "category": "weapon",
               "mats": {"metal": "steel", "grip": "leather_black", "accent": "silver", "wood": "wood"}},
    "axe": {"fn": items.axe, "variants": ["battle", "double"], "scale": 1.0, "category": "weapon",
            "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "spear": {"fn": items.spear, "variants": ["leaf", "pike"], "scale": 1.0, "category": "weapon",
              "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "mace": {"fn": items.mace, "variants": ["flanged", "round"], "scale": 1.0, "category": "weapon",
             "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "staff": {"fn": items.staff, "variants": ["gem", "ornament"], "scale": 1.0, "category": "weapon",
              "mats": {"metal": "silver", "grip": "wood", "accent": "silver", "wood": "wood"}},
    "bow": {"fn": items.bow, "variants": ["recurve", "longbow"], "scale": 1.0, "category": "weapon",
            "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "shield": {"fn": items.shield, "variants": ["round", "kite", "heater"], "scale": 1.0,
               "category": "armor",
               "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "wood"}},
}

SIZE_SCALE = {"small": 0.78, "normal": 1.0, "large": 1.3, "huge": 1.65}


def template_names() -> list:
    return list(TEMPLATES)


def is_template(name: str) -> bool:
    return name in TEMPLATES


def variants_for(name: str) -> list:
    return list(TEMPLATES[name]["variants"])


def default_variant(name: str) -> str:
    return TEMPLATES[name]["variants"][0]

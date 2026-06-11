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
    "greatsword": {"fn": items.greatsword, "variants": ["straight", "curved", "leaf"], "scale": 1.0,
                   "category": "weapon",
                   "mats": {"metal": "steel", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "dagger": {"fn": items.dagger, "variants": ["straight", "curved", "leaf"], "scale": 1.0,
               "category": "weapon",
               "mats": {"metal": "steel", "grip": "leather_black", "accent": "silver", "wood": "wood"}},
    "katana": {"fn": items.katana, "variants": ["uchigatana", "wakizashi", "great", "nodachi"], "scale": 1.0,
               "category": "weapon",
               "mats": {"metal": "steel", "grip": "leather_black", "accent": "iron", "wood": "dark_wood"}},
    "thrusting_sword": {"fn": items.thrusting_sword, "variants": ["rapier", "estoc", "heavy", "stitcher"],
                        "scale": 1.0, "category": "weapon",
                        "mats": {"metal": "steel", "grip": "leather", "accent": "silver", "wood": "wood"}},
    "twinblade": {"fn": items.twinblade, "variants": ["balanced", "peeler", "leaf", "ornate"],
                  "scale": 1.0, "category": "weapon",
                  "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "wood"}},
    "axe": {"fn": items.axe, "variants": ["battle", "double", "crescent", "cleaver"], "scale": 1.0, "category": "weapon",
            "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "hammer": {"fn": items.hammer, "variants": ["warhammer", "club", "pick", "spiked", "great"],
               "scale": 1.0, "category": "weapon",
               "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "spear": {"fn": items.spear, "variants": ["leaf", "pike"], "scale": 1.0, "category": "weapon",
              "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "halberd": {"fn": items.halberd, "variants": ["axe", "glaive", "bill", "crescent", "banner"],
                "scale": 1.0, "category": "weapon",
                "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "reaper": {"fn": items.reaper, "variants": ["scythe", "grave", "halo", "winged"], "scale": 1.0,
               "category": "weapon",
               "mats": {"metal": "iron", "grip": "leather", "accent": "silver", "wood": "dark_wood"}},
    "mace": {"fn": items.mace, "variants": ["flanged", "round"], "scale": 1.0, "category": "weapon",
             "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "flail": {"fn": items.flail, "variants": ["spiked", "chainlink", "round"], "scale": 1.0,
              "category": "weapon",
              "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "staff": {"fn": items.staff, "variants": ["gem", "ornament"], "scale": 1.0, "category": "weapon",
              "mats": {"metal": "silver", "grip": "wood", "accent": "silver", "wood": "wood"}},
    "sacred_seal": {"fn": items.sacred_seal, "variants": ["finger", "order", "clawmark", "spiral"],
                    "scale": 1.0, "category": "catalyst",
                    "mats": {"metal": "gold", "grip": "cloth", "accent": "gold", "wood": "wood"}},
    "bow": {"fn": items.bow, "variants": ["recurve", "longbow"], "scale": 1.0, "category": "weapon",
            "mats": {"metal": "steel", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "greatbow": {"fn": items.greatbow, "variants": ["great", "golem", "horn"], "scale": 1.0,
                 "category": "weapon",
                 "mats": {"metal": "iron", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "crossbow": {"fn": items.crossbow, "variants": ["light", "heavy", "repeating", "pulley"], "scale": 1.0,
                 "category": "weapon",
                 "mats": {"metal": "iron", "grip": "leather", "accent": "bronze", "wood": "dark_wood"}},
    "torch": {"fn": items.torch, "variants": ["flame", "ghostflame", "sentry", "wire"], "scale": 1.0,
              "category": "tool",
              "mats": {"metal": "iron", "grip": "leather", "accent": "bronze", "wood": "wood"}},
    "claw": {"fn": items.claw, "variants": ["hook", "talon", "beast"], "scale": 1.0,
             "category": "weapon",
             "mats": {"metal": "steel", "grip": "leather_black", "accent": "iron", "wood": "wood"}},
    "fist": {"fn": items.fist, "variants": ["caestus", "spiked", "katar"], "scale": 1.0,
             "category": "weapon",
             "mats": {"metal": "iron", "grip": "leather", "accent": "iron", "wood": "wood"}},
    "perfume_bottle": {"fn": items.perfume_bottle, "variants": ["round", "faceted", "fire", "lightning", "poison"],
                       "scale": 1.0, "category": "tool",
                       "mats": {"metal": "silver", "grip": "cloth", "accent": "silver", "wood": "wood"}},
    "shield": {"fn": items.shield, "variants": ["round", "kite", "heater", "buckler", "great", "tower",
                                                "palisade", "thrusting"], "scale": 1.0,
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

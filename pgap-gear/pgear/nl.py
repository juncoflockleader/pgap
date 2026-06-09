"""Prompt → gear spec (deterministic keyword inference).

"a curved iron sword with a leather grip" → {template: sword, variant: curved,
material: "iron leather", size: normal}. Material keywords are left in the string
for the material resolver. Unrecognized → a plain steel sword (with a warning)."""

from __future__ import annotations

import re
from typing import Any, Dict

from .registry import default_variant, variants_for

# template -> trigger words (first match by scan order wins; multi-word score higher)
_TEMPLATE_KW = {
    "greatsword": ["greatsword", "great sword", "claymore", "zweihander", "two-handed sword"],
    "dagger": ["dagger", "knife", "dirk", "stiletto"],
    "axe": ["axe", "battleaxe", "hatchet", "waraxe"],
    "spear": ["spear", "lance", "pike", "polearm", "halberd", "glaive"],
    "mace": ["mace", "hammer", "maul", "warhammer", "club"],
    "staff": ["staff", "wand", "rod", "scepter", "sceptre"],
    "bow": ["bow", "longbow", "recurve"],
    "shield": ["shield", "buckler", "kite shield", "heater"],
    "sword": ["sword", "blade", "sabre", "saber", "scimitar", "katana", "rapier", "falchion"],
}
_VARIANT_KW = {
    "curved": ["curved", "scimitar", "sabre", "saber", "katana", "falchion"],
    "leaf": ["leaf", "leaf-blade", "leaf blade"],
    "double": ["double", "double-bladed", "twin", "two-headed"],
    "flanged": ["flanged"],
    "round": ["round"],
    "kite": ["kite"],
    "heater": ["heater"],
    "pike": ["pike", "long"],
    "longbow": ["longbow"],
    "recurve": ["recurve"],
    "gem": ["gem", "crystal", "jewel"],
    "ornament": ["ornate", "ornament", "carved"],
}
_SIZE_KW = {"huge": ["huge", "giant", "massive", "colossal"],
            "large": ["large", "heavy", "big"],
            "small": ["small", "short", "mini", "light"]}


def _camel(text: str) -> str:
    return "".join(w.capitalize() for w in re.findall(r"[a-z0-9]+", text.lower())[:3]) or "Gear"


def prompt_to_spec(prompt: str, seed: int = 0) -> Dict[str, Any]:
    text = prompt.lower()
    warnings = []

    template, best = None, 0
    for name, kws in _TEMPLATE_KW.items():
        for kw in kws:
            if kw in text:
                score = len(kw.split()) + 0.1
                if score > best:
                    template, best = name, score
    if template is None:
        template, warnings = "sword", ["no gear type recognized; defaulting to a sword"]

    variant = default_variant(template)
    for v, kws in _VARIANT_KW.items():
        if v in variants_for(template) and any(k in text for k in kws):
            variant = v
            break

    size = "normal"
    for s, kws in _SIZE_KW.items():
        if any(k in text for k in kws):
            size = s
            break

    spec = {"name": _camel(prompt), "template": template, "variant": variant,
            "material": prompt, "size": size, "seed": int(seed)}
    return {"ok": True, "spec": spec, "warnings": warnings}

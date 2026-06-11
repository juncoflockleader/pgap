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
    "greatsword": ["colossal sword", "greatsword", "great sword", "claymore", "zweihander", "two-handed sword"],
    "dagger": ["dagger", "knife", "dirk", "stiletto"],
    "katana": ["great katana", "katana", "uchigatana", "wakizashi", "nodachi", "samurai blade"],
    "thrusting_sword": ["heavy thrusting sword", "thrusting sword", "rapier", "estoc", "great epee", "stitcher"],
    "twinblade": ["twinblade", "twin blade", "poleblade", "double-ended sword"],
    "axe": ["axe", "battleaxe", "hatchet", "waraxe", "cleaver"],
    "hammer": ["great hammer", "warhammer", "hammer", "club", "maul", "warpick", "pickaxe"],
    "spear": ["spear", "lance", "pike", "harpoon"],
    "halberd": ["halberd", "glaive", "polearm", "swordspear", "naginata", "billhook"],
    "reaper": ["reaper", "scythe", "grave scythe", "sickle"],
    "mace": ["mace", "morning star", "scepter", "sceptre"],
    "flail": ["flail", "chain flail", "chainlink flail"],
    "staff": ["staff", "wand", "rod"],
    "sacred_seal": ["sacred seal", "seal", "finger seal", "clawmark seal", "spiraltree seal"],
    "greatbow": ["greatbow", "great bow"],
    "crossbow": ["crossbow", "arbalest", "ballista"],
    "torch": ["torch", "ghostflame torch", "sentry torch"],
    "claw": ["beast claw", "claw", "hookclaw", "hookclaws", "talons"],
    "fist": ["fist", "caestus", "katar", "pata"],
    "perfume_bottle": ["perfume bottle", "perfume", "aromatic bottle"],
    "bow": ["bow", "longbow", "recurve"],
    "shield": ["thrusting shield", "greatshield", "great shield", "tower shield", "shield", "buckler", "kite shield", "heater"],
    "sword": ["straight sword", "light greatsword", "sword", "blade", "sabre", "saber", "scimitar", "falchion"],
}
_VARIANT_KW = {
    "curved": ["curved", "scimitar", "sabre", "saber", "katana", "falchion"],
    "leaf": ["leaf", "leaf-blade", "leaf blade"],
    "uchigatana": ["uchigatana", "samurai"],
    "wakizashi": ["wakizashi", "short katana"],
    "nodachi": ["nodachi"],
    "rapier": ["rapier"],
    "estoc": ["estoc"],
    "heavy": ["heavy thrusting", "great epee", "epee", "stitcher"],
    "stitcher": ["stitcher"],
    "balanced": ["twinblade", "twin blade"],
    "peeler": ["peeler", "poleblade"],
    "ornate": ["ornate", "ornament", "ornamental", "coded"],
    "double": ["double", "double-bladed", "twin", "two-headed"],
    "crescent": ["crescent"],
    "cleaver": ["cleaver", "butcher"],
    "warhammer": ["warhammer", "hammer"],
    "club": ["club"],
    "pick": ["pick", "warpick", "pickaxe"],
    "spiked": ["spiked", "spike", "morning star"],
    "axe": ["axe halberd", "standard halberd"],
    "glaive": ["glaive", "swordspear", "naginata"],
    "bill": ["bill", "billhook", "hooked"],
    "banner": ["banner", "standard"],
    "grave": ["grave", "grave scythe", "black"],
    "scythe": ["scythe", "sickle"],
    "halo": ["halo", "holy"],
    "winged": ["winged"],
    "chainlink": ["chainlink", "chain-link"],
    "flanged": ["flanged"],
    "round": ["round"],
    "buckler": ["buckler"],
    "tower": ["tower", "towershield"],
    "palisade": ["palisade"],
    "thrusting": ["thrusting shield", "dueling shield"],
    "kite": ["kite"],
    "heater": ["heater"],
    "pike": ["pike", "long"],
    "longbow": ["longbow"],
    "recurve": ["recurve"],
    "golem": ["golem"],
    "horn": ["horn", "horn bow"],
    "great": ["greatshield", "great shield", "greatbow", "great bow", "great katana", "great hammer"],
    "light": ["light crossbow", "shortbow", "light bow"],
    "repeating": ["repeating", "repeater"],
    "pulley": ["pulley"],
    "ghostflame": ["ghostflame", "ghost flame"],
    "sentry": ["sentry"],
    "wire": ["wire", "steel-wire"],
    "hook": ["hookclaw", "hookclaws", "hook"],
    "talon": ["talon", "talons", "raptor"],
    "beast": ["beast claw", "beast"],
    "caestus": ["caestus"],
    "katar": ["katar", "pata"],
    "finger": ["finger seal", "finger"],
    "order": ["golden order", "order"],
    "clawmark": ["clawmark"],
    "spiral": ["spiral", "spiraltree"],
    "faceted": ["faceted"],
    "fire": ["fire", "firespark"],
    "lightning": ["lightning"],
    "poison": ["poison"],
    "gem": ["gem", "crystal", "jewel"],
    "ornament": ["ornament", "carved"],
}
_SIZE_KW = {"huge": ["huge", "giant", "massive", "colossal"],
            "large": ["large", "heavy", "big"],
            "small": ["small", "short", "mini", "light"]}


def _camel(text: str) -> str:
    return "".join(w.capitalize() for w in re.findall(r"[a-z0-9]+", text.lower())[:3]) or "Gear"


def _has_kw(text: str, kw: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text) is not None


def prompt_to_spec(prompt: str, seed: int = 0) -> Dict[str, Any]:
    text = prompt.lower()
    warnings = []

    template, best = None, 0
    for name, kws in _TEMPLATE_KW.items():
        for kw in kws:
            if _has_kw(text, kw):
                score = len(kw.split()) + 0.1
                if score > best:
                    template, best = name, score
    if template is None:
        template, warnings = "sword", ["no gear type recognized; defaulting to a sword"]

    variant = default_variant(template)
    variant_best = 0.0
    for v, kws in _VARIANT_KW.items():
        if v not in variants_for(template):
            continue
        for kw in kws:
            if _has_kw(text, kw):
                score = len(kw.split()) + 0.1
                if score > variant_best:
                    variant, variant_best = v, score

    size = "normal"
    for s, kws in _SIZE_KW.items():
        if any(_has_kw(text, k) for k in kws):
            size = s
            break

    spec = {"name": _camel(prompt), "template": template, "variant": variant,
            "material": prompt, "size": size, "seed": int(seed)}
    return {"ok": True, "spec": spec, "warnings": warnings}

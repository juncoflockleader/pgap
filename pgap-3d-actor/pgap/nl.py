"""Deterministic natural-language → spec inference (M7 front-end).

Maps a short prompt to a structured spec dict via keyword tables. This is the
offline, deterministic interface an LLM would otherwise fill — and exactly what
``capabilities.validate_spec`` guards. No network; same prompt → same spec.

Pair with ``capabilities.validate_spec`` to fail closed on anything unsupported
(e.g. an unrecognized creature leaves the archetype unset → validation errors).
"""

from __future__ import annotations

import re

# keyword -> canonical species; the category implies the archetype.
_QUADRUPED = {
    "retriever": "dog", "puppy": "dog", "dog": "dog", "hound": "dog",
    "cat": "cat", "horse": "horse", "wolf": "wolf", "fox": "fox",
    "deer": "deer", "bear": "bear", "lion": "lion", "tiger": "tiger",
}
_BIPED = {
    "human": "humanoid", "person": "humanoid", "man": "humanoid", "woman": "humanoid",
    "robot": "humanoid", "biped": "humanoid", "humanoid": "humanoid",
    "character": "humanoid", "knight": "humanoid", "zombie": "humanoid",
}
_PROP = {
    "rock": "rock", "boulder": "rock", "stone": "rock",
    "barrel": "barrel", "cask": "barrel",
}

_DEFAULT_HEIGHT = {"quadruped": 60.0, "biped": 180.0, "prop": 50.0}
_DEFAULT_COAT = {"quadruped": "warm golden", "biped": "tan", "prop": "grey stone"}
_COLOR_WORDS = ("golden", "gold", "tan", "brown", "chocolate", "black",
                "cream", "white", "grey", "gray", "stone", "granite", "wood", "wooden")


def _first_match(text: str, table: dict) -> tuple[int, str | None, str | None]:
    best = (len(text) + 1, None, None)
    for kw, species in table.items():
        idx = text.find(kw)
        if 0 <= idx < best[0]:
            best = (idx, kw, species)
    return best


def _camel(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:3]
    return "".join(w.capitalize() for w in words) or "Actor"


def prompt_to_spec(prompt: str, seed: int = 12345) -> dict:
    """Infer a spec dict from a prompt. Archetype is left unset if unrecognized
    (so validate_spec fails closed)."""
    text = prompt.lower()

    # Archetype + species: whichever category keyword appears earliest.
    cands = []
    for arch, table in (("quadruped", _QUADRUPED), ("biped", _BIPED), ("prop", _PROP)):
        idx, kw, species = _first_match(text, table)
        if kw is not None:
            cands.append((idx, arch, species))
    spec: dict = {"seed": int(seed), "style": "stylized_low_poly"}
    if not cands:
        spec["archetype"] = None  # fail closed downstream
        spec["species"] = "creature"
        spec["name"] = _camel(prompt)
        return spec
    cands.sort()
    _, archetype, species = cands[0]
    spec["archetype"] = archetype
    spec["species"] = species
    spec["name"] = _camel(species if species else prompt)

    # Coat / material.
    colors = [c for c in _COLOR_WORDS if c in text]
    base_color = " ".join(dict.fromkeys(colors)) if colors else _DEFAULT_COAT[archetype]
    if "darker ear" in text or "dark ear" in text:
        base_color += ", darker ears"
    spec["material"] = {"baseColor": base_color, "fur": archetype == "quadruped"}

    # Traits (quadruped).
    if archetype == "quadruped":
        traits: dict = {}
        if "floppy" in text:
            traits["ears"] = "floppy"
        elif "pointy" in text or "pricked" in text:
            traits["ears"] = "pointy"
        if "long snout" in text or "long muzzle" in text:
            traits["snout"] = "long"
        elif "short snout" in text or "short muzzle" in text:
            traits["snout"] = "short"
        if "feather" in text:
            traits["tail"] = "feathered"
        if traits:
            spec["traits"] = traits

    # Proportions.
    props: dict = {"heightCm": _DEFAULT_HEIGHT[archetype]}
    if "tall" in text or "big" in text or "large" in text:
        props["heightCm"] *= 1.4
    if "small" in text or "tiny" in text or "little" in text:
        props["heightCm"] *= 0.7
    if "long-bodied" in text or "long body" in text:
        props["bodyLength"] = 1.25
    if "long legs" in text or "long-legged" in text:
        props["legLength"] = 1.25
    if "long tail" in text:
        props["tail"] = 1.4
    spec["proportions"] = props

    # Animations.
    anims = []
    if "wag" in text:
        anims.append("tail_wag")
    if "walk" in text or "walking" in text:
        anims.append("walk")
    if "run" in text or "running" in text:
        anims.append("run")
    if "bark" in text:
        anims.append("bark_pose")
    if "idle" in text and "idle" not in anims:
        anims.append("idle")
    if anims:
        spec["animations"] = anims

    return spec

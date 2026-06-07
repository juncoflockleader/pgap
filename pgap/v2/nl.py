"""Natural-language → recipe (V2-M5).

Deterministic keyword inference that turns a prompt into a v2 creature:

- **strict** (default): map the prompt to the nearest preset *template*
  ("a winged lion with a human head" → sphinx). Reliably recognizable.
- **free**: *compose* a recipe from feature keywords (base + wings + tentacles +
  tail + …). More open; validated by the grammar and **falls back to the nearest
  template** if the composition doesn't validate.

Both paths fail closed: an unrecognizable prompt with no template match returns
``ok=False``. No network — the offline interface an LLM targets (or replaces by
emitting a recipe JSON directly).
"""

from __future__ import annotations

import re

from .recipe import recipe_from_dict, validate_recipe
from .registry import TEMPLATE_HEIGHT_CM, load_template

# template -> trigger phrases (multi-word phrases score higher).
_TEMPLATE_KEYWORDS = {
    "beholder": ["beholder", "floating eye", "eye monster", "eye tyrant", "eyestalk", "eye stalk"],
    "octopus_dragon": ["octopus dragon", "octopus-dragon", "tentacled dragon", "dragon octopus"],
    "kraken": ["kraken", "octopus", "squid", "cephalopod"],
    "merfolk": ["mermaid", "merfolk", "merman", "merperson", "siren", "fish tail", "fish-tailed"],
    "cthulhu": ["cthulhu", "great old one", "tentacle face", "tentacled face", "facial tentacle"],
    "sphinx": ["sphinx", "winged lion", "manticore"],
    "biped": ["humanoid", "human ", "person", "robot", "android", "warrior", "knight"],
}

_COLOR_WORDS = ("golden", "gold", "tan", "brown", "chocolate", "black", "cream",
                "white", "grey", "gray", "stone", "green", "teal", "purple",
                "violet", "red", "crimson", "blue", "pink", "pale")


def _camel(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:3]
    return "".join(w.capitalize() for w in words) or "Creature"


def _coat(text: str) -> str:
    found = [c for c in _COLOR_WORDS if c in text]
    return " ".join(dict.fromkeys(found)) if found else "stone"


def _size_mult(text: str) -> float:
    if any(k in text for k in ("giant", "huge", "colossal", "massive", "great")):
        return 1.6
    if any(k in text for k in ("tiny", "small", "little", "miniature")):
        return 0.6
    return 1.0


def _best_template(text: str):
    scores = {name: 0 for name in _TEMPLATE_KEYWORDS}
    for name, kws in _TEMPLATE_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                scores[name] += len(kw.split())
    # heuristic combos for descriptive (un-named) prompts
    if "wing" in text and any(k in text for k in ("lion", "cat", "feline")):
        scores["sphinx"] += 2
    if "lion" in text and ("human" in text or "person" in text):
        scores["sphinx"] += 2
    if "dragon" in text and any(k in text for k in ("tentacle", "octopus")):
        scores["octopus_dragon"] += 3
    if "wing" in text and ("human" in text or "humanoid" in text) and "tentacle" in text:
        scores["cthulhu"] += 2
    best = max(scores, key=lambda k: scores[k])
    return (best, scores[best]) if scores[best] > 0 else (None, 0)


def _compose_free(text: str, name: str) -> dict:
    """Best-effort module composition from feature keywords."""
    modules: list[dict] = []
    if any(k in text for k in ("floating eye", "eye monster", "beholder", "orb", "sphere", "eyeball")):
        base = "orb"
        modules.append({"id": "orb", "kind": "orb"})
    elif any(k in text for k in ("dragon", "lizard", "beast", "lion", "wolf", "drake", "wyvern", "quadruped", "four legs", "four-legged")):
        base = "body"
        modules.append({"id": "body", "kind": "body"})
    else:
        base = "spine"
        modules.append({"id": "spine", "kind": "spine"})

    head_variant = None
    if base == "orb":
        modules.append({"id": "eye", "kind": "eyeball", "attach": "orb.front"})
    else:
        neck_kind = "dragon_neck" if base == "body" else "neck"
        modules.append({"id": "neck", "kind": neck_kind, "attach": f"{base}.neck"})
        head_variant = "humanoid"
        if any(k in text for k in ("dragon", "draconic", "horn", "horned")):
            head_variant = "draconic"
        if "cthulhu" in text or ("tentacle" in text and ("face" in text or "mouth" in text)):
            head_variant = "cephalopod"
        modules.append({"id": "head", "kind": "head", "variant": head_variant, "attach": "neck.top"})

    if base == "orb" and any(k in text for k in ("eyestalk", "eye stalk", "many eyes", "beholder")):
        modules.append({"id": "stalk", "kind": "eyestalk", "attach": "orb.eyes_ring"})

    if any(k in text for k in ("tentacle", "octopus", "squid", "kraken")):
        if base == "orb":
            modules.append({"id": "arms", "kind": "tentacle", "attach": "orb.arms_ring"})
        elif head_variant == "cephalopod":
            modules.append({"id": "face", "kind": "tentacle", "attach": "head.face"})
        elif base == "body":
            modules.append({"id": "arms", "kind": "tentacle", "attach": "body.rear_ring"})

    if "wing" in text and base in ("body", "spine"):
        wing_variant = "bat"
        if any(k in text for k in ("feather", "swan", "angel", "bird", "eagle")):
            wing_variant = "feathered"
        elif any(k in text for k in ("insect", "fairy", "dragonfly", "butterfly")):
            wing_variant = "insect"
        elif any(k in text for k in ("glider", "membrane", "leathery")):
            wing_variant = "membrane"
        modules.append({"id": "wing", "kind": "wing", "variant": wing_variant,
                        "attach": f"{base}.wings", "mirror": True})

    if base == "body":
        modules.append({"id": "foreleg", "kind": "leg", "attach": "body.shoulder", "mirror": True})
        if "no legs" not in text:
            modules.append({"id": "hindleg", "kind": "leg", "attach": "body.hip", "mirror": True})
    elif base == "spine":
        modules.append({"id": "arm", "kind": "arm", "attach": "spine.shoulder", "mirror": True})
        if any(k in text for k in ("mermaid", "fish tail", "merfolk", "serpent tail", "fish-tailed")):
            modules.append({"id": "tail", "kind": "serpent_tail", "attach": "spine.base"})
            modules.append({"id": "fin", "kind": "fin", "attach": "tail.tip"})
        elif "no legs" not in text:
            modules.append({"id": "leg", "kind": "leg", "attach": "spine.hip", "mirror": True})

    return {"name": name, "modules": modules}


_BASE_HEIGHT = {"orb": 80.0, "body": 130.0, "spine": 180.0}


def prompt_to_recipe(prompt: str, seed: int = 5, mode: str = "strict") -> dict:
    """Infer a creature from a prompt. Returns a dict with ``ok`` and, when ok,
    a built ``recipe`` plus name/seed/heightCm/material for generation."""
    text = prompt.lower()
    name = _camel(prompt)
    coat = {"baseColor": _coat(text)}
    mult = _size_mult(text)
    warnings: list[str] = []

    if mode == "free":
        composed = _compose_free(text, name)
        report = validate_recipe(composed)
        if report["ok"] and len(composed["modules"]) >= 2:
            base_kind = composed["modules"][0]["kind"]
            return {"ok": True, "mode": "free", "name": name,
                    "recipe": recipe_from_dict(composed), "recipe_dict": composed,
                    "seed": seed, "heightCm": _BASE_HEIGHT.get(base_kind, 120.0) * mult,
                    "material": coat, "warnings": report["warnings"]}
        warnings.append("free composition did not validate; falling back to nearest template")

    template, score = _best_template(text)
    if template is None:
        return {"ok": False, "mode": mode, "warnings": warnings,
                "errors": [f"could not recognize a creature in {prompt!r}; "
                           f"try naming one of the templates or use --free with features"]}
    return {"ok": True, "mode": "strict", "name": name, "template": template,
            "recipe": load_template(template), "seed": seed,
            "heightCm": TEMPLATE_HEIGHT_CM[template] * mult, "material": coat,
            "warnings": warnings}

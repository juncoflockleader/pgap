"""Prompt → city spec (FR9): deterministic keyword inference.

Maps a free-text prompt ("a rain-soaked cyberpunk downtown", "a quiet japanese
town") to a validated-shape city spec — era/culture cell + size + density. No
network; pure keyword matching. Unrecognized culture falls back to american with a
warning (the spec validator still fail-closes on an unsupported cell).
"""

from __future__ import annotations

import re
from typing import Any, Dict

from .styles import STYLE_PROFILES

_CULTURE_KW = {
    "cyberpunk": ["cyberpunk", "cyber", "neon", "rain-soaked", "rain soaked", "dystopian",
                  "blade runner", "night city", "megacity", "chrome", "hacker"],
    "steampunk": ["steampunk", "brass", "victorian", "airship", "dirigible", "steam",
                  "gears", "clockwork", "industrial revolution", "cogs"],
    "japan": ["japan", "japanese", "tokyo", "osaka", "anime", "kyoto", "shibuya", "akihabara"],
    "american": ["american", "america", "manhattan", "downtown usa", "midwest", "suburb",
                 "new york", "u.s.", "us city"],
}
_ERA_BY_CULTURE = {"cyberpunk": "futuristic", "steampunk": "futuristic",
                   "japan": "modern", "american": "modern"}


def _camel(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:3]
    return "".join(w.capitalize() for w in words) or "City"


def _size(text: str):
    if any(k in text for k in ("huge", "sprawling", "metropolis", "massive", "vast")):
        return [7, 7]
    if any(k in text for k in ("large", "big", "expansive")):
        return [6, 6]
    if any(k in text for k in ("block", "district", "downtown", "neighborhood", "neighbourhood")):
        return [3, 3]
    if any(k in text for k in ("tiny", "small", "village", " town")):  # leading space: not down-town
        return [2, 2]
    return [4, 4]


def _density(text: str):
    if any(k in text for k in ("dense", "packed", "crowded", "bustling", "teeming", "overbuilt")):
        return 0.95
    if any(k in text for k in ("sparse", "quiet", "empty", "suburban", "spread out", "sleepy")):
        return 0.45
    return None  # use the cell's profile default


def prompt_to_spec(prompt: str, seed: int = 0) -> Dict[str, Any]:
    """Return {ok, spec, warnings}. ``spec`` is ready for ``validate_spec``."""
    text = prompt.lower()
    warnings = []

    culture, best = None, 0
    for c, kws in _CULTURE_KW.items():
        score = sum(1 for k in kws if k in text)
        if score > best:
            best, culture = score, c
    if culture is None:
        culture, warnings = "american", ["no style keyword recognized; defaulting to american"]

    era = "futuristic" if any(k in text for k in ("futuristic", "future", "sci-fi", "scifi")) \
        else _ERA_BY_CULTURE[culture]
    if (era, culture) not in STYLE_PROFILES:        # keep the cell valid
        era = _ERA_BY_CULTURE[culture]

    spec: Dict[str, Any] = {"name": _camel(prompt), "era": era, "culture": culture,
                            "seed": int(seed), "sizeBlocks": _size(text)}
    dens = _density(text)
    if dens is not None:
        spec["density"] = dens
    return {"ok": True, "spec": spec, "warnings": warnings}

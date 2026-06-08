"""Capability report + spec validation (FR7).

The capability report is the machine-readable contract of what the generator
supports — an LLM/human front-end reads it to author valid specs. ``validate_spec``
is the gate it calls before generation: it **fails closed** on requests the
generator can't honor (unsupported archetype) and clamps/warns on the rest
(unknown trait value, unavailable animation, unknown species, out-of-range
proportion), returning a normalized spec dict.

No network, fully deterministic.
"""

from __future__ import annotations

from typing import Any

from . import palette, texture
from .animation import ARCHETYPE_CLIPS
from .parts import KNOWN_SPECIES
from .skeleton import EAR_STYLE_NAMES
from .spec import DEFAULT_PROPORTIONS, DEFAULT_TRAITS, SUPPORTED_ARCHETYPES

TRAIT_VOCAB = {
    "ears": list(EAR_STYLE_NAMES),          # floppy | pointy
    "snout": ["short", "medium", "long"],
    "tail": ["feathered", "plain"],
}
PROPORTION_RANGES = {
    "bodyLength": (0.5, 2.0),
    "legLength": (0.5, 2.0),
    "neck": (0.5, 2.0),
    "tail": (0.3, 2.0),
    "arm": (0.5, 2.0),
    "heightCm": (3.0, 500.0),
}
PROP_KINDS = ("rock", "barrel")


def capability_report() -> dict:
    """The supported-feature contract for the front-end."""
    return {
        "schemaVersion": "pgap.capabilities.v1",
        "archetypes": list(SUPPORTED_ARCHETYPES),
        "speciesWithPartLibrary": list(KNOWN_SPECIES),
        "propKinds": list(PROP_KINDS),
        "traits": {k: list(v) for k, v in TRAIT_VOCAB.items()},
        "animationsByArchetype": {k: list(v) for k, v in ARCHETYPE_CLIPS.items()},
        "coatKeywords": list(palette.COAT_KEYWORDS),
        "irisKeywords": list(palette.IRIS_KEYWORDS),
        "surfaces": list(texture.SURFACES),
        "proportionRanges": {k: list(v) for k, v in PROPORTION_RANGES.items()},
    }


def validate_spec(data: dict[str, Any]) -> dict:
    """Validate/normalize a raw spec dict against capabilities.

    Returns ``{ok, errors, warnings, normalized}``. ``ok`` is False only on a hard
    (fail-closed) error; soft issues are clamped and reported as warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []
    spec = dict(data)

    archetype = spec.get("archetype")
    if archetype not in SUPPORTED_ARCHETYPES:
        errors.append(f"unsupported archetype {archetype!r}; supported: {list(SUPPORTED_ARCHETYPES)}")
        return {"ok": False, "errors": errors, "warnings": warnings, "normalized": spec}

    # Species: unknown quadruped species loses its part library (generic blob).
    species = str(spec.get("species", "")).lower()
    if archetype == "quadruped" and species not in KNOWN_SPECIES:
        warnings.append(f"species {species!r} has no part library; generating a generic quadruped")
    if archetype == "prop" and not any(k in species for k in PROP_KINDS):
        warnings.append(f"prop species {species!r} unknown; defaulting to rock shape")

    # Traits: clamp unknown values to defaults.
    traits = dict(spec.get("traits") or {})
    for key, allowed in TRAIT_VOCAB.items():
        if key in traits and str(traits[key]) not in allowed:
            warnings.append(f"trait {key}={traits[key]!r} not in {allowed}; using {DEFAULT_TRAITS[key]!r}")
            traits[key] = DEFAULT_TRAITS[key]
    if traits:
        spec["traits"] = traits

    # Animations: drop clips unavailable for this archetype.
    available = set(ARCHETYPE_CLIPS.get(archetype, ()))
    anims = spec.get("animations")
    if isinstance(anims, list):
        kept = [a for a in anims if a in available]
        dropped = [a for a in anims if a not in available]
        if dropped:
            warnings.append(f"animations {dropped} unavailable for {archetype}; dropped")
        spec["animations"] = kept

    # Proportions: clamp to supported ranges.
    props = dict(spec.get("proportions") or {})
    for key, value in list(props.items()):
        if key in PROPORTION_RANGES and isinstance(value, (int, float)):
            lo, hi = PROPORTION_RANGES[key]
            if value < lo or value > hi:
                clamped = max(lo, min(hi, value))
                warnings.append(f"proportion {key}={value} out of [{lo},{hi}]; clamped to {clamped}")
                props[key] = clamped
    if props:
        spec["proportions"] = props

    return {"ok": True, "errors": errors, "warnings": warnings, "normalized": spec}

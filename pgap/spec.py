"""Actor spec: M1 subset of the PRD §7 schema.

M0 parsed only the geometry-relevant fields; M1 adds proportions, traits, and the
import-sidecar fields (targetSkeletonName, tailBone) the rig/skinning/assembler
now consume. Unknown keys are preserved in ``extra`` and ignored, so a richer spec
still loads forward-compatibly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_ARCHETYPES = ("prop", "quadruped", "biped")  # M6: prop + biped added

# Reference proportions; spec values multiply these (heightCm is absolute cm).
DEFAULT_PROPORTIONS = {
    "bodyLength": 1.0,
    "legLength": 1.0,
    "neck": 1.0,
    "tail": 1.0,
    "heightCm": 60.0,
}
DEFAULT_TRAITS = {
    "ears": "floppy",
    "snout": "medium",
    "tail": "feathered",
}
DEFAULT_ANIMATIONS = ("idle", "walk", "tail_wag", "bark_pose")
DEFAULT_MATERIAL = {
    "baseColor": "warm golden",
    "fur": True,
    "roughness": 0.9,
}


@dataclass(frozen=True)
class Spec:
    """Validated actor spec (M1 subset)."""

    name: str
    archetype: str
    species: str
    seed: int
    tri_budget: int
    proportions: dict
    traits: dict
    target_skeleton: str
    tail_bone: str
    animations: list
    material: dict
    extra: dict = field(default_factory=dict)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Spec":
        if not isinstance(data, dict):
            raise ValueError("spec must be a JSON object")

        archetype = data.get("archetype")
        if archetype not in SUPPORTED_ARCHETYPES:
            raise ValueError(
                f"unsupported archetype {archetype!r}; "
                f"M1 supports {SUPPORTED_ARCHETYPES}"
            )

        seed = data.get("seed")
        if not isinstance(seed, int):
            raise ValueError("spec.seed must be an integer (determinism)")

        tri_budget = data.get("triBudget", 8000)
        if not isinstance(tri_budget, int) or tri_budget <= 0:
            raise ValueError("spec.triBudget must be a positive integer")

        proportions = {**DEFAULT_PROPORTIONS, **(data.get("proportions") or {})}
        for key, value in proportions.items():
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"spec.proportions.{key} must be a positive number")

        traits = {**DEFAULT_TRAITS, **(data.get("traits") or {})}
        species = str(data.get("species", "creature"))
        name = str(data.get("name", species))

        animations = data.get("animations")
        if animations is None:
            animations = list(DEFAULT_ANIMATIONS)
        elif not isinstance(animations, list) or not all(isinstance(a, str) for a in animations):
            raise ValueError("spec.animations must be a list of clip-name strings")

        material = {**DEFAULT_MATERIAL, **(data.get("material") or {})}

        known = {
            "archetype", "species", "seed", "triBudget", "name",
            "proportions", "traits", "targetSkeletonName", "tailBone", "animations",
            "material",
        }
        extra = {k: v for k, v in data.items() if k not in known}

        return Spec(
            name=name,
            archetype=str(archetype),
            species=species,
            seed=seed,
            tri_budget=tri_budget,
            proportions=proportions,
            traits=traits,
            target_skeleton=str(data.get("targetSkeletonName", f"SKEL_{name}")),
            tail_bone=str(data.get("tailBone", "tail_01")),
            animations=animations,
            material=material,
            extra=extra,
        )

    @staticmethod
    def load(path: str | Path) -> "Spec":
        text = Path(path).read_text(encoding="utf-8")
        return Spec.from_dict(json.loads(text))

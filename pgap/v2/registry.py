"""Module + template registry (V2-M2).

Maps string `kind`s (what a JSON recipe references) to module factories, and
template names to preset recipe factories. This is the vocabulary an LLM/human
composes from; the grammar validator and capability report read it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import library as L
from .types import Module, Recipe


@dataclass(frozen=True)
class ModuleEntry:
    factory: Callable          # (params: dict) -> Module
    params: tuple = ()         # accepted param names (for the capability report)


# kind -> how to build it. Param-less modules ignore the params dict.
MODULE_REGISTRY: dict[str, ModuleEntry] = {
    "spine": ModuleEntry(lambda p: L.spine_module()),
    "body": ModuleEntry(lambda p: L.body_module()),
    "neck": ModuleEntry(lambda p: L.neck_module()),
    "dragon_neck": ModuleEntry(lambda p: L.dragon_neck_module()),
    "head": ModuleEntry(lambda p: L.head_module()),
    "draconic_head": ModuleEntry(lambda p: L.draconic_head_module()),
    "arm": ModuleEntry(lambda p: L.arm_module()),
    "leg": ModuleEntry(lambda p: L.leg_module()),
    "tentacle": ModuleEntry(lambda p: L.tentacle_module()),
    "orb": ModuleEntry(
        lambda p: L.orb_module(radius=float(p.get("radius", 0.24)),
                               eye_ring=int(p.get("eye_ring", 8)),
                               arm_ring=int(p.get("arm_ring", 8))),
        params=("radius", "eye_ring", "arm_ring"),
    ),
    "eyeball": ModuleEntry(lambda p: L.eyeball_module(radius=float(p.get("radius", 0.11))),
                           params=("radius",)),
    "eyestalk": ModuleEntry(lambda p: L.eyestalk_module(eye_radius=float(p.get("eye_radius", 0.05))),
                            params=("eye_radius",)),
    "wing": ModuleEntry(lambda p: L.wing_module()),
    "fin": ModuleEntry(lambda p: L.fin_module()),
    "serpent_tail": ModuleEntry(lambda p: L.serpent_tail_module()),
}

# template name -> preset recipe factory (accepts override kwargs).
TEMPLATE_REGISTRY: dict[str, Callable] = {
    "biped": lambda **o: L.biped_recipe(),
    "beholder": lambda **o: L.beholder_recipe(eyes=int(o.get("eyes", 8))),
    "kraken": lambda **o: L.kraken_recipe(arms=int(o.get("arms", 8))),
    "octopus_dragon": lambda **o: L.octopus_dragon_recipe(),
    "sphinx": lambda **o: L.sphinx_recipe(),
    "merfolk": lambda **o: L.merfolk_recipe(),
}

# Sensible default standing height (cm) per template, for the CLI.
TEMPLATE_HEIGHT_CM: dict[str, float] = {
    "biped": 180, "beholder": 80, "kraken": 70,
    "octopus_dragon": 130, "sphinx": 120, "merfolk": 175,
}


def build_module(kind: str, params: dict | None = None) -> Module:
    entry = MODULE_REGISTRY.get(kind)
    if entry is None:
        raise KeyError(f"unknown module kind {kind!r}")
    return entry.factory(params or {})


def load_template(name: str, overrides: dict | None = None) -> Recipe:
    factory = TEMPLATE_REGISTRY.get(name)
    if factory is None:
        raise KeyError(f"unknown creature template {name!r}")
    return factory(**(overrides or {}))

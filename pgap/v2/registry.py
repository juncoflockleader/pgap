"""Module + template registry (V2-M2, + V3-M0 variant tables).

Maps string `kind`s to **variant tables** (a kind is a slot; a variant is the
form, e.g. head: humanoid|draconic|cephalopod), and template names to preset
recipe factories. This is the vocabulary an LLM/human composes from; the grammar
validator, capability report, and NL front-end read it.

Backward compatible: a recipe that omits `variant` gets the kind's default;
legacy kind names (`draconic_head`, `cephalopod_head`) resolve via ALIASES.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import library as L
from .types import Module, Recipe


@dataclass(frozen=True)
class ModuleKind:
    default: str                       # default variant name
    variants: dict                     # name -> (params: dict) -> Module
    params: tuple = field(default_factory=tuple)  # accepted param names


def _single(factory: Callable, params: tuple = ()) -> ModuleKind:
    """A kind with one (default) variant — the v2 single-form modules."""
    return ModuleKind(default="default", variants={"default": factory}, params=params)


# kind -> variant table.
MODULE_REGISTRY: dict[str, ModuleKind] = {
    "spine": _single(lambda p: L.spine_module()),
    "body": _single(lambda p: L.body_module()),
    "neck": _single(lambda p: L.neck_module()),
    "dragon_neck": _single(lambda p: L.dragon_neck_module()),
    # head is the V3-M0 demonstration: one slot, three existing forms.
    "head": ModuleKind(
        default="humanoid",
        variants={
            "humanoid": lambda p: L.head_module(),
            "draconic": lambda p: L.draconic_head_module(),
            "cephalopod": lambda p: L.cephalopod_head_module(),
        },
    ),
    "arm": _single(lambda p: L.arm_module()),
    "leg": _single(lambda p: L.leg_module()),
    "tentacle": _single(lambda p: L.tentacle_module()),
    "orb": ModuleKind(
        default="default",
        variants={"default": lambda p: L.orb_module(
            radius=float(p.get("radius", 0.24)), eye_ring=int(p.get("eye_ring", 8)),
            arm_ring=int(p.get("arm_ring", 8)))},
        params=("radius", "eye_ring", "arm_ring"),
    ),
    "eyeball": ModuleKind(default="default",
                          variants={"default": lambda p: L.eyeball_module(radius=float(p.get("radius", 0.11)))},
                          params=("radius",)),
    "eyestalk": ModuleKind(default="default",
                           variants={"default": lambda p: L.eyestalk_module(eye_radius=float(p.get("eye_radius", 0.05)))},
                           params=("eye_radius",)),
    "wing": ModuleKind(default="bat", variants={
        "bat": lambda p: L.wing_module(),
        "feathered": lambda p: L.wing_feathered_module(),
        "membrane": lambda p: L.wing_membrane_module(),
        "insect": lambda p: L.wing_insect_module(),
    }),
    "fin": _single(lambda p: L.fin_module()),
    "serpent_tail": _single(lambda p: L.serpent_tail_module()),
    "horn": ModuleKind(default="unicorn", variants={
        "unicorn": lambda p: L.horn_unicorn_module(),
        "antler": lambda p: L.horn_antler_module(),
        "ram": lambda p: L.horn_ram_module(),
        "bull": lambda p: L.horn_bull_module(),
        "rhino": lambda p: L.horn_rhino_module(),
    }),
}

# Legacy kind name -> (canonical kind, forced variant). Keeps old JSON valid.
ALIASES: dict[str, tuple] = {
    "draconic_head": ("head", "draconic"),
    "cephalopod_head": ("head", "cephalopod"),
}

TEMPLATE_REGISTRY: dict[str, Callable] = {
    "biped": lambda **o: L.biped_recipe(),
    "beholder": lambda **o: L.beholder_recipe(eyes=int(o.get("eyes", 8))),
    "kraken": lambda **o: L.kraken_recipe(arms=int(o.get("arms", 8))),
    "octopus_dragon": lambda **o: L.octopus_dragon_recipe(),
    "sphinx": lambda **o: L.sphinx_recipe(),
    "merfolk": lambda **o: L.merfolk_recipe(),
    "cthulhu": lambda **o: L.cthulhu_recipe(),
    "unicorn": lambda **o: L.unicorn_recipe(),
    "stag": lambda **o: L.stag_recipe(),
}

TEMPLATE_HEIGHT_CM: dict[str, float] = {
    "biped": 180, "beholder": 80, "kraken": 70,
    "octopus_dragon": 130, "sphinx": 120, "merfolk": 175, "cthulhu": 240,
    "unicorn": 160, "stag": 150,
}


def resolve_kind(kind: str) -> tuple:
    """(canonical_kind, forced_variant_or_None). Raises KeyError if unknown."""
    if kind in MODULE_REGISTRY:
        return kind, None
    if kind in ALIASES:
        return ALIASES[kind]
    raise KeyError(f"unknown module kind {kind!r}")


def known_kind(kind: str) -> bool:
    return kind in MODULE_REGISTRY or kind in ALIASES


def variant_names(kind: str) -> list:
    canon, _ = resolve_kind(kind)
    return list(MODULE_REGISTRY[canon].variants)


def build_module(kind: str, variant: str | None = None, params: dict | None = None) -> Module:
    canon, forced = resolve_kind(kind)
    mk = MODULE_REGISTRY[canon]
    v = forced or variant or mk.default
    if v not in mk.variants:
        raise KeyError(f"unknown variant {v!r} for kind {canon!r}; have {list(mk.variants)}")
    return mk.variants[v](params or {})


def load_template(name: str, overrides: dict | None = None) -> Recipe:
    factory = TEMPLATE_REGISTRY.get(name)
    if factory is None:
        raise KeyError(f"unknown creature template {name!r}")
    return factory(**(overrides or {}))

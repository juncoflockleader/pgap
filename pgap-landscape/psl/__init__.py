"""psl — Procedural Landscape Pipeline (pgap-landscape).

Deterministic, offline biome terrain: a 16-bit heightmap (+ per-layer weightmaps,
tiling textures, scatter rules in later milestones) handed to unreal-mcp-rx.

Scaffold status (L0): spec + fail-closed validator + capability report + a
deterministic heightmap for the `plain` biome. Surfacing (weightmaps/textures),
scatter, water, and biome-specific landforms are later milestones (L1–L5) — see
PRD.md. The pgap ⇄ engine boundary is SPLIT.md at the repo root.
"""

from __future__ import annotations

from .capabilities import capabilities
from .spec import BIOMES, validate_spec
from .pipeline import generate

__all__ = ["capabilities", "validate_spec", "generate", "BIOMES"]

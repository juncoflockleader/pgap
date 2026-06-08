"""psc — Procedural City Pipeline (pgap-city).

Deterministic, offline city generation: a modular building kit + a city layout
graph (streets -> blocks -> lots -> instance transforms + props), handed to
unreal-mcp-rx to import and bulk-instance.

Scaffold status (C0): style registry for the four v1 cells + spec + fail-closed
validator + capability report + a deterministic grid **layout** (instance
transforms). The building-kit glTF assembly (reusing the pgap-3d-actor module
engine), roads, and props land in C1+ (see PRD.md). Boundary: repo-root SPLIT.md.
"""

from __future__ import annotations

from .capabilities import capabilities
from .spec import CELLS, CULTURES, ERAS, validate_spec
from .pipeline import generate

__all__ = ["capabilities", "validate_spec", "generate", "ERAS", "CULTURES", "CELLS"]

"""pgap-gear (pgear) — deterministic, offline procedural gear (weapons + shields).

A rigid static-mesh kit composed from part modules (blade + guard + grip + pommel,
haft + head, …) with named variants, the way pgap-3d-actor composes creatures. A
spec/prompt -> a multi-material glTF + preview + import sidecar + manifest.
"""

from .capabilities import capabilities
from .pipeline import generate
from .spec import validate_spec

__all__ = ["capabilities", "generate", "validate_spec"]

"""psap — Procedural Sound Asset Pipeline.

Deterministic, dependency-light, offline synthesis of game-ready sounds
(SFX / UI / stylized creature vocals) exported as WAV. The audio sibling of
pgap-3d-actor; same architecture (spec -> seeded RNG -> synth -> render -> file +
manifest -> Unreal handoff).
"""

__version__ = "0.1.0"

from .spec import SoundSpec  # noqa: E402
from .pipeline import render_spec, generate  # noqa: E402

__all__ = ["SoundSpec", "render_spec", "generate", "__version__"]

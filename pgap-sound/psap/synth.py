"""Category router: a SoundSpec -> a raw float sample buffer."""

from __future__ import annotations

import numpy as np

from . import sfx, vocal
from .spec import SoundSpec


def synthesize(spec: SoundSpec, rng) -> np.ndarray:
    n = max(1, int(round(spec.sample_rate * spec.duration_ms / 1000.0)))
    if spec.category in ("sfx", "ui"):
        return sfx.synth(spec.graph, n, spec.sample_rate, rng)
    if spec.category == "vocal":
        return vocal.synth(spec.graph, n, spec.sample_rate, rng)
    raise ValueError(f"unsupported category {spec.category!r}")

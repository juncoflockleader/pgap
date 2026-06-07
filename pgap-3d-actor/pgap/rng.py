"""Deterministic RNG spine.

One ``numpy.random.Generator(PCG64(seed))`` is created from the spec seed and
threaded explicitly through every stage. It is never re-seeded mid-pipeline.
See PRD §11 and DESIGN §4.
"""

from __future__ import annotations

import numpy as np

Rng = np.random.Generator


def make_rng(seed: int) -> Rng:
    """Create the single seeded generator for a run.

    PCG64 is portable and reproducible across machines, which is what FR1
    (byte-identical output for the same spec+seed) requires.
    """
    return np.random.Generator(np.random.PCG64(int(seed)))

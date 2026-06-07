"""The determinism spine: one seeded PCG64 generator, threaded explicitly.

Same seed -> identical noise -> identical samples -> byte-identical WAV. Never
re-seed mid-render; never use wall-clock or os.urandom in the core path.
"""

from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    """Return a deterministic numpy Generator for the given integer seed."""
    return np.random.Generator(np.random.PCG64(int(seed)))

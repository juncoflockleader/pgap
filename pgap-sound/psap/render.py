"""Render polish (S1) — DC removal, soft saturation, fades, peak normalization.

Guarantees a loudness-safe, click-free, non-clipping buffer (FR4): the final peak
is exactly the requested dBFS target and |sample| <= 1.0.
"""

from __future__ import annotations

import numpy as np


def db_to_lin(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def finalize(buf, sample_rate: int, peak_dbfs: float = -1.0,
             fade_ms: float = 3.0, saturate: float = 1.2):
    """Polish a raw synth buffer into a final, loudness-safe float signal."""
    x = np.asarray(buf, dtype=np.float64).copy()
    if x.size == 0:
        return x

    # DC offset removal
    x -= x.mean()

    # Gentle soft-clip / saturation (the "soft limiter") — tames transients and
    # adds warmth; normalized so unity input stays ~unity.
    if saturate and saturate > 0:
        x = np.tanh(saturate * x) / np.tanh(saturate)

    # Short fade in/out to kill start/end clicks (skipped entirely when fade_ms<=0,
    # e.g. for seamless loops where an edge fade would re-introduce a seam click).
    f = min(int(round(sample_rate * fade_ms / 1000.0)), x.size // 2)
    if f > 0:
        ramp = np.linspace(0.0, 1.0, f, dtype=np.float64)
        x[:f] *= ramp
        x[-f:] *= ramp[::-1]

    # Peak-normalize to target dBFS (target < 0 dB => guaranteed no clipping).
    peak = float(np.max(np.abs(x)))
    if peak > 1e-9:
        x *= db_to_lin(peak_dbfs) / peak
    return x

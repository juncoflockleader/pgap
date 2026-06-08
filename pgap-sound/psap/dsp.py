"""Core DSP primitives — oscillators, envelopes, a biquad filter, and effects.

All pure numpy, deterministic. The IIR filter uses one hand-rolled Direct-Form-I
recurrence (no scipy) so output bytes are identical on every machine regardless of
what's installed.
"""

from __future__ import annotations

import numpy as np

TWO_PI = 2.0 * np.pi

WAVES = ("sine", "square", "saw", "triangle", "noise")


def oscillator(wave: str, freq, n: int, sr: int, rng=None, phase0: float = 0.0):
    """Generate `n` samples of `wave` at `freq` Hz.

    `freq` may be a scalar (constant pitch) or an array of length `n` (a sweep /
    pitch contour). `noise` ignores freq and draws from `rng`.
    """
    if wave == "noise":
        if rng is None:
            raise ValueError("noise oscillator requires an rng")
        return rng.uniform(-1.0, 1.0, size=n).astype(np.float64)

    if np.isscalar(freq):
        phase = phase0 + TWO_PI * float(freq) * np.arange(n, dtype=np.float64) / sr
    else:
        f = np.asarray(freq, dtype=np.float64)
        if f.shape[0] != n:
            raise ValueError("freq array length must equal n")
        phase = phase0 + np.cumsum(TWO_PI * f / sr)

    if wave == "sine":
        return np.sin(phase)
    if wave == "square":
        return np.sign(np.sin(phase))
    if wave == "saw":
        x = phase / TWO_PI
        return 2.0 * (x - np.floor(0.5 + x))
    if wave == "triangle":
        return (2.0 / np.pi) * np.arcsin(np.sin(phase))
    raise ValueError(f"unknown wave {wave!r}")


def envelope(n: int, sr: int, attack_ms: float = 2.0, decay_ms: float = 120.0,
             hold_ms: float = 0.0, sustain: float = 0.0, curve: str = "exp"):
    """Attack -> hold -> decay (-> sustain) amplitude envelope, length `n`.

    `sustain` is the floor the decay falls to (0.0 for a one-shot). `exp` curve
    gives a natural percussive decay; `lin` is linear.
    """
    a = max(1, int(round(sr * attack_ms / 1000.0)))
    h = max(0, int(round(sr * hold_ms / 1000.0)))
    d = max(1, int(round(sr * decay_ms / 1000.0)))
    t = np.arange(n, dtype=np.float64)
    env = np.full(n, sustain, dtype=np.float64)

    ae = min(a, n)
    if ae > 0:
        env[:ae] = t[:ae] / a

    hs, he = a, min(a + h, n)
    if he > hs:
        env[hs:he] = 1.0

    ds, de = a + h, min(a + h + d, n)
    if de > ds:
        k = (t[ds:de] - (a + h)) / d
        if curve == "exp":
            env[ds:de] = sustain + (1.0 - sustain) * np.exp(-5.0 * k)
        else:
            env[ds:de] = sustain + (1.0 - sustain) * (1.0 - k)
    return env


def _biquad(x, b0, b1, b2, a1, a2):
    """Direct-Form-I recurrence (deterministic, no scipy)."""
    xs = np.asarray(x, dtype=np.float64).tolist()
    out = [0.0] * len(xs)
    x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(xs):
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out[i] = yi
        x2, x1 = x1, xi
        y2, y1 = y1, yi
    return np.asarray(out, dtype=np.float64)


def biquad_lowpass(x, sr: int, cutoff: float, q: float = 0.707):
    """RBJ-cookbook lowpass."""
    cutoff = float(np.clip(cutoff, 20.0, sr * 0.45))
    q = max(1e-3, float(q))
    w0 = TWO_PI * cutoff / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * q)
    a0 = 1.0 + alpha
    b0 = (1.0 - cw) / 2.0 / a0
    b1 = (1.0 - cw) / a0
    b2 = b0
    a1 = (-2.0 * cw) / a0
    a2 = (1.0 - alpha) / a0
    return _biquad(x, b0, b1, b2, a1, a2)


def biquad_highpass(x, sr: int, cutoff: float, q: float = 0.707):
    """RBJ-cookbook highpass."""
    cutoff = float(np.clip(cutoff, 20.0, sr * 0.45))
    q = max(1e-3, float(q))
    w0 = TWO_PI * cutoff / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * q)
    a0 = 1.0 + alpha
    b0 = (1.0 + cw) / 2.0 / a0
    b1 = -(1.0 + cw) / a0
    b2 = b0
    a1 = (-2.0 * cw) / a0
    a2 = (1.0 - alpha) / a0
    return _biquad(x, b0, b1, b2, a1, a2)


def biquad_bandpass(x, sr: int, freq: float, q: float = 5.0):
    """RBJ-cookbook bandpass (constant 0 dB peak gain) — one formant resonance."""
    freq = float(np.clip(freq, 20.0, sr * 0.45))
    q = max(0.1, float(q))
    w0 = TWO_PI * freq / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * q)
    a0 = 1.0 + alpha
    b0 = alpha / a0
    b1 = 0.0
    b2 = -alpha / a0
    a1 = (-2.0 * cw) / a0
    a2 = (1.0 - alpha) / a0
    return _biquad(x, b0, b1, b2, a1, a2)


def formant_bank(x, sr: int, formants):
    """Sum parallel bandpass resonances (source-filter vocal shaping).

    `formants` is a list of [freq, q, gain] (q and gain optional). The result is
    normalized to the input's peak so it mixes cleanly with the dry source.
    """
    out = np.zeros_like(np.asarray(x, dtype=np.float64))
    for f in formants:
        freq = float(f[0])
        q = float(f[1]) if len(f) > 1 else 6.0
        gain = float(f[2]) if len(f) > 2 else 1.0
        out += gain * biquad_bandpass(x, sr, freq, q)
    peak = np.max(np.abs(out))
    if peak > 1e-9:
        out *= (np.max(np.abs(x)) + 1e-9) / peak
    return out


def bitcrush(x, bits: int = 6, downsample: int = 2):
    """Quantize to `bits` and sample-and-hold by `downsample` — retro/8-bit grit."""
    bits = int(np.clip(bits, 1, 16))
    levels = float(2 ** bits)
    step = 2.0 / (levels - 1.0)
    y = np.round(np.asarray(x, dtype=np.float64) / step) * step
    downsample = max(1, int(downsample))
    if downsample > 1:
        n = y.shape[0]
        idx = (np.arange(n) // downsample) * downsample
        idx = np.clip(idx, 0, n - 1)
        y = y[idx]
    return y

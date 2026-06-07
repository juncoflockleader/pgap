"""A shared post-synthesis effects bus — reverb, delay, chorus, distortion.

Effects run as an ordered chain (`spec.effects`) on any category's buffer, after
synthesis and before the final loudness pass. They lift perceived quality across
the board and are the composable "recipe" layer for audio (source -> fx1 -> fx2).

All effects are deterministic (any noise is drawn from the passed RNG). Reverb,
delay and chorus take a `loop` flag: when true they wrap around the buffer
(circular convolution / np.roll / modulo read) so a seamless ambient loop *stays*
seamless.
"""

from __future__ import annotations

import numpy as np

from . import dsp


def _next_pow2(n: int) -> int:
    return 1 << max(0, (n - 1).bit_length())


def reverb(x, sr, rng, decay=0.5, wet=0.3, damping=0.5, loop=False):
    """Convolution reverb with a procedurally-generated decaying-noise impulse."""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    ir_len = max(1, int(sr * decay * 2.5))
    if loop:
        ir_len = min(ir_len, n)
    t = np.arange(ir_len, dtype=np.float64) / sr
    ir = rng.uniform(-1.0, 1.0, ir_len) * np.exp(-t / max(1e-3, decay))
    if damping and damping > 0:
        ir = dsp.biquad_lowpass(ir, sr, sr * 0.5 * (1.0 - 0.9 * float(damping)))
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9

    if loop:
        N = n
    else:
        N = _next_pow2(n + ir_len - 1)
    wet_sig = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n]
    wet_sig *= (np.max(np.abs(x)) + 1e-9) / (np.max(np.abs(wet_sig)) + 1e-9)
    return (1.0 - wet) * x + wet * wet_sig


def delay(x, sr, rng, time_ms=150.0, feedback=0.4, wet=0.35, taps=10, loop=False):
    """Feedback echo, expanded into a finite sum of decaying delayed taps."""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    d = max(1, int(sr * time_ms / 1000.0))
    echoes = np.zeros(n, dtype=np.float64)
    g = float(feedback)
    for k in range(1, int(taps) + 1):
        if g < 1e-3:
            break
        if loop:
            echoes += g * np.roll(x, k * d)
        elif k * d < n:
            s = np.zeros(n, dtype=np.float64)
            s[k * d:] = x[: n - k * d]
            echoes += g * s
        g *= float(feedback)
    return x + wet * echoes


def chorus(x, sr, rng, rate_hz=1.5, depth_ms=3.0, base_ms=12.0, wet=0.4, loop=False):
    """LFO-modulated short delay mixed with the dry signal (fattening/shimmer)."""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    idx0 = np.arange(n, dtype=np.float64)
    base = base_ms / 1000.0 * sr
    depth = depth_ms / 1000.0 * sr
    mod = base + depth * (0.5 * (1.0 + np.sin(dsp.TWO_PI * rate_hz * idx0 / sr)))
    read = idx0 - mod
    if loop:
        read = np.mod(read, n)
        i0 = np.floor(read).astype(int)
        frac = read - i0
        wet_sig = x[i0] * (1.0 - frac) + x[(i0 + 1) % n] * frac
    else:
        wet_sig = np.interp(np.clip(read, 0, n - 1), idx0, x)
    return (1.0 - 0.5 * wet) * x + 0.5 * wet * wet_sig


def distortion(x, sr, rng, drive=4.0, wet=1.0, loop=False):
    """tanh waveshaping (saturation -> overdrive as drive rises)."""
    x = np.asarray(x, dtype=np.float64)
    d = max(1e-3, float(drive))
    shaped = np.tanh(d * x) / np.tanh(d)
    return (1.0 - wet) * x + wet * shaped


EFFECTS = {
    "reverb": reverb,
    "delay": delay,
    "chorus": chorus,
    "distortion": distortion,
}
EFFECT_NAMES = tuple(EFFECTS)


def apply_chain(x, sr, rng, chain, loop=False):
    """Run an ordered list of {type, **params} effect specs over `x`."""
    out = np.asarray(x, dtype=np.float64)
    for eff in chain:
        if not isinstance(eff, dict) or "type" not in eff:
            raise ValueError(f"effect must be an object with a 'type': {eff!r}")
        fn = EFFECTS.get(eff["type"])
        if fn is None:
            raise ValueError(f"unknown effect {eff['type']!r}; known: {list(EFFECT_NAMES)}")
        params = {k: v for k, v in eff.items() if k != "type"}
        out = fn(out, sr, rng, loop=loop, **params)
    return out

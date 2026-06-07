"""Ambient loops — wind, rain, fire, water, hum, drone.

Texture = filtered/granular noise (and, for tonal beds, a few low sines) shaped by
a slow amplitude LFO. The one genuinely new piece vs. one-shots is **seamless
looping**: synthesize `n + xfade` samples, then equal-power crossfade the
continuation just past the end back over the head — so playing `out[n-1] -> out[0]`
is a *real consecutive sample pair* of the underlying signal, with no click.

A graph: highpass/lowpass (band of the noise bed, Hz), noise (bed gain 0..1),
tone (list of Hz for a tonal drone), crackle/crackle_rate (sparse pops, for fire),
lfo_hz/lfo_depth (gusts/tremolo), xfade_ms (loop crossfade length).
"""

from __future__ import annotations

import numpy as np

from . import dsp

# preset -> {duration_ms, graph}
AMBIENT_PRESETS: dict[str, dict] = {
    "wind": {"duration_ms": 2500, "graph": {
        "highpass": 140, "lowpass": 900, "noise": 1.0,
        "lfo_hz": 0.3, "lfo_depth": 0.6, "xfade_ms": 250}},
    "rain": {"duration_ms": 2500, "graph": {
        "highpass": 1500, "lowpass": 9000, "noise": 1.0,
        "lfo_hz": 0.0, "lfo_depth": 0.0, "xfade_ms": 200}},
    "fire": {"duration_ms": 2500, "graph": {
        "lowpass": 420, "noise": 0.7, "crackle": 0.6, "crackle_rate": 34,
        "lfo_hz": 0.5, "lfo_depth": 0.3, "xfade_ms": 250}},
    "water": {"duration_ms": 2500, "graph": {
        "highpass": 300, "lowpass": 2200, "noise": 1.0,
        "lfo_hz": 3.0, "lfo_depth": 0.4, "xfade_ms": 220}},
    "hum": {"duration_ms": 2000, "graph": {
        "tone": [60, 120, 180], "noise": 0.12, "lowpass": 2000,
        "lfo_hz": 4.0, "lfo_depth": 0.12, "xfade_ms": 200}},
    "drone": {"duration_ms": 2500, "graph": {
        "tone": [55, 82.5, 110], "noise": 0.2, "lowpass": 600,
        "lfo_hz": 0.15, "lfo_depth": 0.25, "xfade_ms": 300}},
}
for _preset in AMBIENT_PRESETS.values():
    _preset["category"] = "ambient"


def _crackle(n: int, sr: int, rng, rate: float) -> np.ndarray:
    out = np.zeros(n, dtype=np.float64)
    count = int(rate * n / sr)
    if count <= 0:
        return out
    pop = int(0.004 * sr)
    decay = 0.0015 * sr
    shape = np.exp(-np.arange(pop) / decay)
    for p in rng.integers(0, n, size=count):
        e = min(n, p + pop)
        out[p:e] += float(rng.uniform(-1.0, 1.0)) * shape[: e - p]
    return out


def _texture(g: dict, n: int, sr: int, rng) -> np.ndarray:
    t = np.arange(n, dtype=np.float64) / sr
    out = np.zeros(n, dtype=np.float64)

    tones = g.get("tone", [])
    for f in tones:
        out += np.sin(dsp.TWO_PI * float(f) * t) / max(1, len(tones))

    noise_gain = float(g.get("noise", 1.0))
    if noise_gain > 0.0:
        nz = dsp.oscillator("noise", 0, n, sr, rng)
        if g.get("highpass"):
            nz = dsp.biquad_highpass(nz, sr, float(g["highpass"]))
        if g.get("lowpass"):
            nz = dsp.biquad_lowpass(nz, sr, float(g["lowpass"]))
        out += noise_gain * nz

    crackle = float(g.get("crackle", 0.0))
    if crackle > 0.0:
        out += crackle * _crackle(n, sr, rng, float(g.get("crackle_rate", 30.0)))

    lfo_hz = float(g.get("lfo_hz", 0.0))
    depth = float(g.get("lfo_depth", 0.0))
    if lfo_hz > 0.0 and depth > 0.0:
        lfo = 1.0 - depth * 0.5 * (1.0 + np.sin(dsp.TWO_PI * lfo_hz * t))
        out = out * lfo
    return out


def synth(g: dict, n: int, sr: int, rng) -> np.ndarray:
    """Render a seamlessly-looping ambient buffer of length `n`."""
    xf = min(int(sr * float(g.get("xfade_ms", 200)) / 1000.0), n // 2)
    raw = _texture(g, n + xf, sr, rng)
    if xf <= 0:
        return raw[:n]

    out = raw[:n].copy()
    t = np.linspace(0.0, 1.0, xf, endpoint=False)
    w_in = np.sqrt(t)            # equal-power: keeps noise RMS constant across the seam
    w_out = np.sqrt(1.0 - t)
    out[:xf] = raw[n:n + xf] * w_out + raw[:xf] * w_in
    return out

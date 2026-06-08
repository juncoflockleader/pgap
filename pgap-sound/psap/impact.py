"""Impacts via modal synthesis — material collision sounds.

An impact is a bank of decaying sinusoidal *modes* (the object's resonance) excited
by a short noise *contact transient*. The mode ratios encode the material: few
warm fast-decaying modes read as wood; many inharmonic long-ringing modes as metal;
bright brittle modes as glass; a couple of dull fast modes (plus noise) as stone.

A graph: material (preset selector), base_freq (Hz of the fundamental), transient
(0..1 contact-click amount). `partials` may be given explicitly as
[[ratio, gain, decay_s], ...] to override the material bank.
"""

from __future__ import annotations

import numpy as np

from . import dsp

# material -> {duration_ms, base_freq, transient, partials [(freq ratio, gain,
# decay seconds)]}. wood/metal/glass are MEASURED from Kenney Impact Sounds (CC0)
# by psap.analyze (modal analysis of refs/impacts/*.wav) — real resonances, not
# hand-guessed. stone stays hand-tuned (no reference sample yet). Re-derive with:
#   python -m psap.analyze refs/impacts/<mat>_000.wav --material <mat>
MATERIAL_PRESETS: dict[str, dict] = {
    "wood": {"duration_ms": 330, "base_freq": 172.27, "transient": 0.5, "partials": [
        (1.0, 1.0, 0.0424), (1.625, 0.9032, 0.0274)]},
    "metal": {"duration_ms": 269, "base_freq": 839.79, "transient": 0.5, "partials": [
        (1.0, 0.4877, 0.0309), (1.1795, 1.0, 0.0309), (2.6154, 0.16, 0.0306),
        (3.5641, 0.4167, 0.0307)]},
    "glass": {"duration_ms": 540, "base_freq": 904.39, "transient": 0.5, "partials": [
        (1.0, 1.0, 0.0765), (1.5476, 0.0327, 0.0828), (1.619, 0.2197, 0.0771),
        (1.7381, 0.3303, 0.0767)]},
    "stone": {"duration_ms": 240, "base_freq": 180.0, "transient": 0.50, "partials": [
        (1.0, 1.0, 0.06), (1.42, 0.5, 0.05), (1.93, 0.3, 0.04)]},
}

# preset entries (so the NL/preset path and corpus can enumerate impacts)
IMPACT_PRESETS: dict[str, dict] = {
    name: {"category": "impact", "duration_ms": m["duration_ms"], "graph": {
        "material": name, "base_freq": m["base_freq"], "transient": m["transient"]}}
    for name, m in MATERIAL_PRESETS.items()
}


def synth(g: dict, n: int, sr: int, rng) -> np.ndarray:
    """Render an impact graph to a raw float buffer of length `n`."""
    base = float(g.get("base_freq", 300.0))
    partials = g.get("partials")
    if not partials:
        mat = g.get("material", "wood")
        partials = MATERIAL_PRESETS.get(mat, MATERIAL_PRESETS["wood"])["partials"]

    t = np.arange(n, dtype=np.float64) / sr
    out = np.zeros(n, dtype=np.float64)
    nyq = sr * 0.5
    for ratio, gain, decay in partials:
        f = base * float(ratio)
        if f >= nyq:
            continue
        env = np.exp(-t / max(1e-3, float(decay)))
        out += float(gain) * env * np.sin(dsp.TWO_PI * f * t)

    transient = float(g.get("transient", 0.3))
    if transient > 0.0:
        click = dsp.oscillator("noise", 0, n, sr, rng)
        click *= np.exp(-t / 0.006)  # ~6 ms contact burst
        click = dsp.biquad_lowpass(click, sr, float(g.get("transient_cut", base * 6.0)))
        out += transient * click
    return out

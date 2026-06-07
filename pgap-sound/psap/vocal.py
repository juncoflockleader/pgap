"""Stylized creature vocals via FM synthesis + a pitch contour + a noise layer.

A graph: f0/fpeak/f1 (pitch contour Hz), mod_ratio/mod_index (FM timbre),
growl/growl_hz (sub-audio amplitude modulation), noise/noise_cut (breath/rasp),
env {attack, hold, decay, sustain}. The direct analog of pgap-3d-actor's stylized
creatures — a *synthesized* bark, not a recording.
"""

from __future__ import annotations

import numpy as np

from . import dsp

# preset -> {category, duration_ms, graph}
VOCAL_PRESETS: dict[str, dict] = {
    "bark": {"category": "vocal", "duration_ms": 260, "graph": {
        "f0": 280.0, "fpeak": 430.0, "f1": 170.0, "mod_ratio": 1.5, "mod_index": 4.0,
        "growl": 0.3, "growl_hz": 45.0, "noise": 0.25, "noise_cut": 3500.0,
        "env": {"attack": 3, "hold": 40, "decay": 180}}},
    "growl": {"category": "vocal", "duration_ms": 700, "graph": {
        "f0": 130.0, "f1": 105.0, "mod_ratio": 1.0, "mod_index": 4.0,
        "growl": 0.6, "growl_hz": 30.0, "noise": 0.3, "noise_cut": 2500.0,
        "env": {"attack": 20, "hold": 420, "decay": 260}}},
    "roar": {"category": "vocal", "duration_ms": 1200, "graph": {
        "f0": 120.0, "fpeak": 95.0, "f1": 70.0, "mod_ratio": 1.0, "mod_index": 5.0,
        "growl": 0.6, "growl_hz": 26.0, "noise": 0.45, "noise_cut": 2200.0,
        "env": {"attack": 40, "hold": 700, "decay": 460}}},
    "chirp": {"category": "vocal", "duration_ms": 160, "graph": {
        "f0": 1800.0, "fpeak": 2600.0, "f1": 1500.0, "mod_ratio": 3.0, "mod_index": 2.0,
        "growl": 0.0, "noise": 0.1, "noise_cut": 6000.0,
        "env": {"attack": 3, "hold": 20, "decay": 130}}},
    "squeak": {"category": "vocal", "duration_ms": 140, "graph": {
        "f0": 1600.0, "fpeak": 2200.0, "f1": 1700.0, "mod_ratio": 2.0, "mod_index": 3.0,
        "growl": 0.0, "noise": 0.15, "noise_cut": 6000.0,
        "env": {"attack": 2, "hold": 10, "decay": 125}}},
}


def synth(g: dict, n: int, sr: int, rng) -> np.ndarray:
    """Render a vocal graph to a raw float buffer of length `n`."""
    f0 = float(g.get("f0", 220.0))
    f1 = float(g.get("f1", f0))
    fpeak = g.get("fpeak")
    if fpeak is not None:
        half = max(1, n // 2)
        contour = np.concatenate([
            np.linspace(f0, float(fpeak), half),
            np.linspace(float(fpeak), f1, n - half),
        ])
    else:
        contour = np.linspace(f0, f1, n)

    # FM: carrier modulated by a sine at mod_ratio * pitch, depth = mod_index.
    ratio = float(g.get("mod_ratio", 2.0))
    index = float(g.get("mod_index", 3.0))
    modulator = dsp.oscillator("sine", contour * ratio, n, sr, rng) * index
    phase = np.cumsum(dsp.TWO_PI * contour / sr)
    voice = np.sin(phase + modulator)

    growl = float(g.get("growl", 0.0))
    if growl > 0.0:
        ghz = float(g.get("growl_hz", 30.0))
        am = 1.0 - growl * 0.5 * (1.0 + np.sin(dsp.TWO_PI * ghz * np.arange(n) / sr))
        voice = voice * am

    noise_mix = float(g.get("noise", 0.0))
    if noise_mix > 0.0:
        rasp = dsp.biquad_lowpass(dsp.oscillator("noise", 0, n, sr, rng),
                                  sr, float(g.get("noise_cut", 3000.0)))
        voice = (1.0 - noise_mix) * voice + noise_mix * rasp

    dur_ms = n / sr * 1000.0
    env = g.get("env", {})
    voice = voice * dsp.envelope(
        n, sr,
        attack_ms=env.get("attack", 5.0),
        decay_ms=env.get("decay", dur_ms * 0.6),
        hold_ms=env.get("hold", dur_ms * 0.2),
        sustain=env.get("sustain", 0.0),
    )
    return voice

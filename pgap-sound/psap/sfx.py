"""One-shot SFX synthesis (the sfxr model) + a small preset library.

A graph is a flat dict of params:
  wave, freq, sweep (Hz added over the duration), arpeggio (list of semitone
  offsets), noise (0..1 mix), env {attack, decay, hold, sustain}, filter
  {cutoff, q}, fx (["bitcrush", ...]), bits, crush_ds.
"""

from __future__ import annotations

import numpy as np

from . import dsp

# preset -> {category, duration_ms, graph}
SFX_PRESETS: dict[str, dict] = {
    "laser": {"category": "sfx", "duration_ms": 340, "graph": {
        "wave": "square", "freq": 1150.0, "sweep": -820.0,
        "env": {"attack": 1, "decay": 300}, "filter": {"cutoff": 5200, "q": 0.7}}},
    "coin": {"category": "sfx", "duration_ms": 300, "graph": {
        "wave": "square", "freq": 880.0, "arpeggio": [0, 12],
        "env": {"attack": 1, "decay": 270}}},
    "pickup": {"category": "sfx", "duration_ms": 280, "graph": {
        "wave": "triangle", "freq": 700.0, "arpeggio": [0, 7, 12],
        "env": {"attack": 1, "decay": 250}}},
    "powerup": {"category": "sfx", "duration_ms": 460, "graph": {
        "wave": "square", "freq": 520.0, "arpeggio": [0, 4, 7, 12],
        "env": {"attack": 1, "decay": 420}}},
    "jump": {"category": "sfx", "duration_ms": 220, "graph": {
        "wave": "square", "freq": 420.0, "sweep": 520.0,
        "env": {"attack": 1, "decay": 190}}},
    "hit": {"category": "sfx", "duration_ms": 200, "graph": {
        "wave": "square", "freq": 240.0, "sweep": -160.0, "noise": 0.5,
        "env": {"attack": 1, "decay": 170}, "filter": {"cutoff": 3200, "q": 0.7}}},
    "explosion": {"category": "sfx", "duration_ms": 700, "graph": {
        "wave": "noise", "freq": 200.0, "noise": 1.0,
        "env": {"attack": 2, "decay": 650}, "filter": {"cutoff": 1300, "q": 0.6}}},
    "blip": {"category": "ui", "duration_ms": 90, "graph": {
        "wave": "square", "freq": 880.0, "env": {"attack": 1, "decay": 75}}},
}


def synth(g: dict, n: int, sr: int, rng) -> np.ndarray:
    """Render an SFX graph to a raw float buffer of length `n`."""
    wave = g.get("wave", "square")
    freq = float(g.get("freq", 440.0))
    dur_ms = n / sr * 1000.0

    arp = g.get("arpeggio")
    if arp:
        body = np.zeros(n, dtype=np.float64)
        seg = max(1, n // len(arp))
        for i, semitones in enumerate(arp):
            s = i * seg
            e = n if i == len(arp) - 1 else min(n, (i + 1) * seg)
            if e <= s:
                break
            f = freq * (2.0 ** (semitones / 12.0))
            body[s:e] = dsp.oscillator(wave, f, e - s, sr, rng)
    else:
        sweep = float(g.get("sweep", 0.0))
        if abs(sweep) > 1e-9:
            f = np.linspace(freq, max(20.0, freq + sweep), n)
        else:
            f = freq
        body = dsp.oscillator(wave, f, n, sr, rng)

    noise_mix = float(g.get("noise", 0.0))
    if noise_mix > 0.0 and wave != "noise":
        body = (1.0 - noise_mix) * body + noise_mix * dsp.oscillator("noise", 0, n, sr, rng)

    env = g.get("env", {})
    body = body * dsp.envelope(
        n, sr,
        attack_ms=env.get("attack", 2.0),
        decay_ms=env.get("decay", dur_ms * 0.85),
        hold_ms=env.get("hold", 0.0),
        sustain=env.get("sustain", 0.0),
    )

    filt = g.get("filter")
    if filt:
        body = dsp.biquad_lowpass(body, sr, filt.get("cutoff", 6000.0), filt.get("q", 0.707))

    for fx in g.get("fx", []):
        if fx == "bitcrush":
            body = dsp.bitcrush(body, bits=int(g.get("bits", 6)),
                                downsample=int(g.get("crush_ds", 2)))
    return body

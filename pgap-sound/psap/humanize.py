"""Seeded humanization — deterministic per-seed variation of a synth graph.

`variance` in (0, 1] perturbs numeric params by a small, musical amount drawn from
the spec's seeded RNG. So the same (spec, seed) is still byte-identical, but a new
seed gives a different *take* of the same sound — and unlike raw noise, this makes
the seed a variation knob for tonal sounds too (lasers, coins, jumps).

Drawn from the same RNG that later feeds the noise oscillator, so the whole render
stays deterministic. variance == 0 returns the graph untouched (exact preset).
"""

from __future__ import annotations

import copy

import numpy as np

# relative ± perturbation at variance == 1.0 (multiplied by `variance`)
_REL = {
    "freq": 0.10, "f0": 0.10, "fpeak": 0.10, "f1": 0.10,
    "sweep": 0.12, "mod_index": 0.15, "growl_hz": 0.10,
}
_ENV_REL = {"attack": 0.15, "decay": 0.15, "hold": 0.15}


def apply_variance(graph: dict, variance: float, rng) -> dict:
    if not variance or variance <= 0.0:
        return graph
    v = float(min(variance, 1.0))
    g = copy.deepcopy(graph)

    def jitter(rel: float) -> float:
        return 1.0 + v * rel * float(rng.uniform(-1.0, 1.0))

    for key, rel in _REL.items():
        if isinstance(g.get(key), (int, float)) and not isinstance(g[key], bool):
            g[key] = g[key] * jitter(rel)

    env = g.get("env")
    if isinstance(env, dict):
        for key, rel in _ENV_REL.items():
            if isinstance(env.get(key), (int, float)) and not isinstance(env[key], bool):
                env[key] = max(0.0, env[key] * jitter(rel))

    filt = g.get("filter")
    if isinstance(filt, dict) and isinstance(filt.get("cutoff"), (int, float)):
        filt["cutoff"] = filt["cutoff"] * jitter(0.15)

    if isinstance(g.get("noise"), (int, float)) and not isinstance(g["noise"], bool):
        g["noise"] = float(np.clip(g["noise"] + v * 0.05 * rng.uniform(-1.0, 1.0), 0.0, 1.0))
    if isinstance(g.get("growl"), (int, float)) and not isinstance(g["growl"], bool):
        g["growl"] = float(np.clip(g["growl"] * jitter(0.10), 0.0, 1.0))

    return g

"""End-to-end orchestration: spec -> seeded render -> finalized buffer -> files."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .humanize import apply_variance
from .render import finalize
from .rng import make_rng
from .spec import SoundSpec
from .synth import synthesize


def render_spec(spec: SoundSpec) -> np.ndarray:
    """Deterministically render a spec to a final, loudness-safe float buffer.

    Draws seeded humanization first (if spec.variance > 0), then synthesis — all
    from one RNG, so (spec, seed) stays byte-identical while a new seed yields a
    different take.
    """
    rng = make_rng(spec.seed)
    graph = apply_variance(spec.graph, spec.variance, rng)
    raw = synthesize(replace(spec, graph=graph), rng)
    return finalize(raw, spec.sample_rate, peak_dbfs=spec.gain_dbfs)


def generate(spec: SoundSpec, out_dir, handoff: bool = False, package_root=None):
    """Render and write outputs; returns (manifest, buffer)."""
    from .assemble import write_outputs  # local import to avoid a cycle

    buf = render_spec(spec)
    manifest = write_outputs(spec, buf, out_dir, handoff=handoff, package_root=package_root)
    return manifest, buf

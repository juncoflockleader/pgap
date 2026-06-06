"""FR1: same (spec, seed) → byte-identical output.

Written alongside the first geometry code, per CLAUDE.md. Runs the full M0
pipeline twice and asserts the glTF bytes (and their SHA) are identical.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pgap.animation import animate
from pgap.assemble import assemble_gltf
from pgap.pipeline import build_actor
from pgap.rng import make_rng
from pgap.spec import Spec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _build_gltf_bytes() -> bytes:
    spec = Spec.load(FIXTURE)
    rng = make_rng(spec.seed)
    skel, mesh = build_actor(spec, rng)
    clips = animate(skel, spec)
    return assemble_gltf(mesh, spec.name, skel, clips)


def test_gltf_bytes_identical_across_runs():
    a = _build_gltf_bytes()
    b = _build_gltf_bytes()
    assert a == b
    assert hashlib.sha1(a).hexdigest() == hashlib.sha1(b).hexdigest()


def test_gltf_nonempty():
    data = _build_gltf_bytes()
    assert len(data) > 1000  # a real mesh, not an empty document

"""FR4 (M0 subset): the generated mesh is sane enough to import and shade.

Checks single-component, finite coords, within tri budget, normalized normals,
and a low boundary/non-manifold edge count (watertight-enough for stylized).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pgap.geometry import mesh_stats
from pgap.pipeline import build_actor
from pgap.rng import make_rng
from pgap.spec import Spec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dog_golden_retriever.json"


def _build():
    spec = Spec.load(FIXTURE)
    rng = make_rng(spec.seed)
    _, mesh = build_actor(spec, rng)
    return spec, mesh


def test_mesh_nonempty_and_finite():
    spec, mesh = _build()
    stats = mesh_stats(mesh)
    assert stats["vertices"] > 0
    assert stats["triangles"] > 0
    assert stats["finite"]


def test_within_tri_budget():
    spec, mesh = _build()
    assert mesh.num_triangles <= spec.tri_budget


def test_normals_normalized():
    _, mesh = _build()
    lengths = np.linalg.norm(mesh.normals, axis=1)
    assert np.allclose(lengths, 1.0, atol=1e-3)


def test_indices_in_range():
    _, mesh = _build()
    assert mesh.indices.max() < mesh.num_vertices
    assert mesh.indices.shape[0] % 3 == 0


def test_watertight_enough():
    _, mesh = _build()
    stats = mesh_stats(mesh)
    # A closed blob should have very few boundary/non-manifold edges.
    edge_total = stats["triangles"] * 3
    assert stats["boundary_edges"] < 0.02 * edge_total
    assert stats["nonmanifold_edges"] < 0.02 * edge_total

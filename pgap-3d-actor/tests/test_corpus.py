"""M7: golden corpus / variance regression (PRD §9).

Many seeds of each archetype must all produce valid, non-degenerate meshes
("no exploded/degenerate output") and be byte-deterministic per seed.
"""

from __future__ import annotations

import hashlib

import numpy as np

from pgap.assemble import assemble_gltf
from pgap.geometry import mesh_stats
from pgap.pipeline import build_actor, build_bundle
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec

SEEDS = (1, 7, 42, 1234)

_SPECS = {
    "dog": {"archetype": "quadruped", "species": "dog", "triBudget": 9000,
            "traits": {"ears": "floppy", "tail": "feathered"},
            "material": {"baseColor": "warm golden"}},
    "biped": {"archetype": "biped", "species": "humanoid", "triBudget": 8000,
              "proportions": {"heightCm": 180}, "material": {"baseColor": "tan"}},
    "prop": {"archetype": "prop", "species": "rock", "triBudget": 5000,
             "proportions": {"heightCm": 50}, "material": {"baseColor": "grey stone"}},
}


def _spec(kind: str, seed: int) -> Spec:
    return Spec.from_dict({**_SPECS[kind], "name": kind.capitalize(), "seed": seed})


def test_corpus_all_seeds_valid():
    for kind in _SPECS:
        for seed in SEEDS:
            spec = _spec(kind, seed)
            skel, mesh = build_actor(spec, make_rng(seed))
            st = mesh_stats(mesh)
            assert st["triangles"] > 0, (kind, seed)
            assert st["finite"], (kind, seed)
            assert mesh.num_triangles <= spec.tri_budget, (kind, seed)
            edges = st["triangles"] * 3
            # Watertight-enough: very few boundary / non-manifold edges.
            assert st["boundary_edges"] < 0.02 * edges, (kind, seed)
            assert st["nonmanifold_edges"] < 0.02 * edges, (kind, seed)
            if mesh.weights is not None:  # skeletal archetypes
                ss = skin_stats(mesh)
                assert ss["unweighted_vertices"] == 0, (kind, seed)
                assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5), (kind, seed)


def test_corpus_deterministic_per_seed():
    def sha(kind, seed):
        spec = _spec(kind, seed)
        skel, mesh, clips, tex = build_bundle(spec, make_rng(seed))
        return hashlib.sha1(assemble_gltf(mesh, spec.name, skel or None, clips, tex)).hexdigest()

    for kind in _SPECS:
        assert sha(kind, 7) == sha(kind, 7), kind

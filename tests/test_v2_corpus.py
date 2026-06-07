"""V2-M4: every reference chimera generates valid, non-degenerate, deterministic
output across seeds (the v2 golden corpus / variance regression)."""

from __future__ import annotations

import hashlib

import numpy as np

from pgap.assemble import assemble_gltf
from pgap.geometry import mesh_stats
from pgap.rng import make_rng
from pgap.skinning import skin_stats
from pgap.spec import Spec
from pgap.v2.animate import animate_recipe
from pgap.v2.assembly import build_actor
from pgap.v2.registry import TEMPLATE_HEIGHT_CM, TEMPLATE_REGISTRY, load_template

# The five PRD reference chimeras (+ kraken/biped) must all pass.
REFERENCE = ("beholder", "kraken", "octopus_dragon", "sphinx", "merfolk", "cthulhu", "biped")
SEEDS = (1, 7, 42)


def _spec(name, seed):
    return Spec.from_dict({
        "name": name, "archetype": "biped", "species": name, "seed": seed,
        "triBudget": 11000, "proportions": {"heightCm": TEMPLATE_HEIGHT_CM[name]},
        "material": {"baseColor": "stone"},
    })


def test_reference_set_is_registered():
    assert set(REFERENCE) <= set(TEMPLATE_REGISTRY)


def test_corpus_all_creatures_all_seeds_valid():
    for name in REFERENCE:
        for seed in SEEDS:
            spec = _spec(name, seed)
            skel, mesh = build_actor(load_template(name), spec, make_rng(seed))
            st = mesh_stats(mesh)
            tag = (name, seed)
            assert st["triangles"] > 0 and st["finite"], tag
            assert mesh.num_triangles <= spec.tri_budget, tag
            # no exploded / degenerate output:
            assert st["boundary_edges"] < 0.02 * st["triangles"] * 3, tag
            assert st["nonmanifold_edges"] < 0.02 * st["triangles"] * 3, tag
            assert skin_stats(mesh)["unweighted_vertices"] == 0, tag
            assert np.allclose(mesh.weights.sum(axis=1), 1.0, atol=1e-5), tag


def test_corpus_deterministic_per_seed():
    def sha(name, seed):
        spec = _spec(name, seed)
        skel, mesh = build_actor(load_template(name), spec, make_rng(seed))
        clips = animate_recipe(load_template(name), spec)
        return hashlib.sha1(assemble_gltf(mesh, name, skel, clips)).hexdigest()

    for name in REFERENCE:
        assert sha(name, 7) == sha(name, 7), name

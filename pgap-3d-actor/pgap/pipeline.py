"""The pgap generation pipeline (DESIGN §1).

``build_actor`` threads the seeded RNG through skeleton → parts → geometry → skin
→ uv → paint and returns the rig + finished mesh (positions, normals, skin, uvs,
vertex colors). ``build_bundle`` adds the texture synth + animation clips in one
fixed, deterministic order. Both are the single source of truth shared by the CLI
and the tests.
"""

from __future__ import annotations

from .animation import animate
from .archetypes import prop
from .geometry import build_geometry
from .paint import paint_colors
from .parts import build_parts
from .rng import Rng
from .skeleton import build_skeleton
from .skinning import skin
from .spec import Spec
from .texture import synth_textures
from .types import Bone, Mesh
from .uv import layout_uvs


def build_actor(spec: Spec, rng: Rng) -> tuple[list[Bone], Mesh]:
    """Archetype-routed mesh build. Props are rigless static meshes; quadruped
    and biped run the full skeleton-first path (skin + uv + paint)."""
    if spec.archetype == "prop":
        parts = prop.build(spec, rng)
        mesh = build_geometry([], spec, rng, tuple(parts))
        mesh = layout_uvs(mesh, [], spec)
        return [], mesh

    skel = build_skeleton(spec, rng)
    parts = build_parts(skel, spec)
    mesh = build_geometry(skel, spec, rng, tuple(parts))
    mesh = skin(mesh, skel)
    mesh = layout_uvs(mesh, skel, spec)
    mesh = paint_colors(mesh, skel, spec)
    return skel, mesh


def build_bundle(spec: Spec, rng: Rng):
    """Everything needed to assemble: (skel, mesh, clips, textures).

    Fixed order so the seeded RNG (used only by texture synth) is deterministic.
    """
    skel, mesh = build_actor(spec, rng)   # no RNG draws
    textures = synth_textures(spec, rng)  # RNG draws here
    clips = animate(skel, spec)           # no RNG draws
    return skel, mesh, clips, textures

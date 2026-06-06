"""The pgap generation pipeline as one function (DESIGN §1).

``build_actor`` threads the seeded RNG through skeleton → parts → geometry → skin
and returns the rig + finished mesh. Shared by the CLI and the tests so there is a
single source of truth for stage ordering.
"""

from __future__ import annotations

from .geometry import build_geometry
from .parts import build_parts
from .rng import Rng
from .skeleton import build_skeleton
from .skinning import skin
from .spec import Spec
from .types import Bone, Mesh


def build_actor(spec: Spec, rng: Rng) -> tuple[list[Bone], Mesh]:
    skel = build_skeleton(spec, rng)
    parts = build_parts(skel, spec)
    mesh = build_geometry(skel, spec, rng, tuple(parts))
    mesh = skin(mesh, skel)
    return skel, mesh

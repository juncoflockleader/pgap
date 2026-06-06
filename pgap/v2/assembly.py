"""Socket resolver + v2 build path (V2-M0).

``assemble_recipe`` walks a recipe (root first), places each module instance in
world space (mirror expansion for bilateral attachments), names bones uniquely,
and ground-clamps the result into a v1 ``Bone`` list. ``build_actor`` then runs
the *unchanged* v1 geometry → skin → uv → paint stages, proving the heavy pipeline
composes for arbitrary rigs.
"""

from __future__ import annotations

import numpy as np

from ..geometry import build_geometry
from ..paint import paint_colors
from ..rng import Rng
from ..skinning import skin
from ..spec import Spec
from ..types import Bone, Mesh
from ..uv import layout_uvs
from .types import Recipe

_F = np.float32
_REF_HEIGHT_CM = 60.0


class _Placed:
    __slots__ = ("origin", "mirror", "module")

    def __init__(self, origin, mirror, module):
        self.origin = origin
        self.mirror = mirror
        self.module = module


def _instances(att):
    """Expand an attachment into (instance_id, mirror_flag) pairs."""
    if att.mirror:
        return [(f"{att.id}_l", False), (f"{att.id}_r", True)]
    return [(att.id, False)]


def assemble_recipe(recipe: Recipe, spec: Spec) -> list[Bone]:
    mirrored_ids = {a.id for a in recipe.attachments if a.mirror}
    placed: dict[str, _Placed] = {}
    raw: list[tuple] = []  # (name, parent, head, tail, rh, rt, group)

    for att in recipe.attachments:
        for inst_id, mir in _instances(att):
            if att.parent is None:
                origin = np.zeros(3)
                cross_parent = None
            else:
                # Resolve which parent instance this child attaches to.
                if att.parent in mirrored_ids:
                    parent_inst = f"{att.parent}_{'r' if mir else 'l'}"
                else:
                    parent_inst = att.parent
                p = placed[parent_inst]
                sock = p.module.sockets[att.parent_socket]
                spos = sock.position.astype(np.float64).copy()
                if mir:
                    spos[2] *= -1.0
                origin = p.origin + spos
                cross_parent = f"{parent_inst}_{sock.host_bone}"

            placed[inst_id] = _Placed(origin, mir, att.module)

            for b in att.module.bones:
                head = b.head.astype(np.float64).copy()
                tail = b.tail.astype(np.float64).copy()
                if mir:
                    head[2] *= -1.0
                    tail[2] *= -1.0
                head = origin + head
                tail = origin + tail
                parent = f"{inst_id}_{b.parent}" if b.parent else cross_parent
                raw.append((f"{inst_id}_{b.name}", parent, head, tail,
                            b.radius_head, b.radius_tail, b.group))

    # Uniform height scale + ground clamp (matches v1 convention).
    g = float(spec.proportions["heightCm"]) / _REF_HEIGHT_CM
    min_y = min(min(h[1] - rh, t[1] - rt) for _, _, h, t, rh, rt, _ in raw) * g

    bones: list[Bone] = []
    for name, parent, head, tail, rh, rt, group in raw:
        head = head * g
        tail = tail * g
        head[1] -= min_y
        tail[1] -= min_y
        bones.append(
            Bone(name=name, parent=parent, head=head.astype(_F), tail=tail.astype(_F),
                 radius_head=float(rh * g), radius_tail=float(rt * g))
        )
    return bones


def build_actor(recipe: Recipe, spec: Spec, rng: Rng) -> tuple[list[Bone], Mesh]:
    """Recipe → assembled skeleton → v1 geometry/skin/uv/paint (unchanged)."""
    skel = assemble_recipe(recipe, spec)
    mesh = build_geometry(skel, spec, rng, ())
    mesh = skin(mesh, skel)
    mesh = layout_uvs(mesh, skel, spec)
    mesh = paint_colors(mesh, skel, spec)
    return skel, mesh

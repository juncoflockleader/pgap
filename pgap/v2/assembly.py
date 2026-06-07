"""Socket resolver + v2 build path (V2-M0 + V2-M1).

``assemble_recipe`` walks a recipe (root first) and places each module instance in
world space:

- **mirror** attachments → a bilateral pair (`<id>_l` / `<id>_r`, Z-reflected);
- **ring** sockets → N radially-placed, yaw-rotated copies (`<id>_0..N-1`);
- otherwise a single placement.

Each instance carries an origin + rotation; child transforms compose with the
parent's. Bones are named uniquely and ground-clamped into a v1 ``Bone`` list.
``build_actor`` then runs the unchanged v1 geometry → skin → uv → paint stages.
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
_I3 = np.eye(3)


def _roty(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


class _Placed:
    __slots__ = ("origin", "rot", "mirror", "module")

    def __init__(self, origin, rot, mirror, module):
        self.origin = origin
        self.rot = rot
        self.mirror = mirror
        self.module = module


def assemble_recipe(recipe: Recipe, spec: Spec) -> list[Bone]:
    mirrored = {a.id for a in recipe.attachments if a.mirror}
    placed: dict[str, _Placed] = {}
    raw: list[tuple] = []  # (name, parent, head, tail, rh, rt, group)

    for att in recipe.attachments:
        # (instance_id, origin, rot, mirror_flag, cross_parent_bone)
        instances: list[tuple] = []

        if att.parent is None:
            instances.append((att.id, np.zeros(3), _I3, False, None))
        else:
            rep = att.parent if att.parent not in mirrored else f"{att.parent}_l"
            sock = placed[rep].module.sockets[att.parent_socket]
            base = sock.position.astype(np.float64)

            if sock.ring:
                p = placed[att.parent]  # ring hosts are single
                for k in range(int(sock.ring)):
                    rk = _roty(2.0 * np.pi * k / int(sock.ring))
                    offset = rk @ np.array([sock.ring_radius, 0.0, 0.0])
                    origin = p.origin + p.rot @ (base + offset)
                    cross = f"{att.parent}_{sock.host_bone}"
                    instances.append((f"{att.id}_{k}", origin, p.rot @ rk, False, cross))
            elif att.mirror:
                for suffix, mir in (("_l", False), ("_r", True)):
                    parent_inst = att.parent if att.parent not in mirrored else f"{att.parent}_{'r' if mir else 'l'}"
                    p = placed[parent_inst]
                    sp = base.copy()
                    if mir:
                        sp[2] *= -1.0
                    origin = p.origin + p.rot @ sp
                    cross = f"{parent_inst}_{sock.host_bone}"
                    instances.append((f"{att.id}{suffix}", origin, p.rot, mir, cross))
            else:
                p = placed[att.parent]
                origin = p.origin + p.rot @ base
                cross = f"{att.parent}_{sock.host_bone}"
                instances.append((att.id, origin, p.rot, False, cross))

        for inst_id, origin, rot, mir, cross in instances:
            placed[inst_id] = _Placed(origin, rot, mir, att.module)
            for b in att.module.bones:
                head = b.head.astype(np.float64).copy()
                tail = b.tail.astype(np.float64).copy()
                if mir:
                    head[2] *= -1.0
                    tail[2] *= -1.0
                head = origin + rot @ head
                tail = origin + rot @ tail
                parent = f"{inst_id}_{b.parent}" if b.parent else cross
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

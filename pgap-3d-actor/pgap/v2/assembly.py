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


_Z_REFLECT = np.diag([1.0, 1.0, -1.0])


def _euler(rotation) -> np.ndarray:
    """(yaw, pitch, roll) in degrees → a 3×3 rotation about Y, Z, X (in that order).

    Returns the exact identity when all angles are zero, so a default attachment is
    a true no-op and existing creatures stay byte-identical."""
    yaw, pitch, roll = (float(r) for r in rotation)
    if yaw == 0.0 and pitch == 0.0 and roll == 0.0:
        return _I3
    cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
    cr, sr = np.cos(np.radians(roll)), np.sin(np.radians(roll))
    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])     # yaw  (Y)
    rz = np.array([[cp, -sp, 0.0], [sp, cp, 0.0], [0.0, 0.0, 1.0]])     # pitch (Z)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])     # roll  (X)
    return ry @ rz @ rx


class _Placed:
    __slots__ = ("origin", "rot", "mirror", "module")

    def __init__(self, origin, rot, mirror, module):
        self.origin = origin
        self.rot = rot
        self.mirror = mirror
        self.module = module


def assemble_with_meta(recipe: Recipe, spec: Spec):
    """Return (bones, instance_meta). ``instance_meta`` lists one dict per placed
    module instance: {id, kind, local_bones, phase} — consumed by the animator."""
    mirrored = {a.id for a in recipe.attachments if a.mirror}
    placed: dict[str, _Placed] = {}
    raw: list[tuple] = []  # (name, parent, head, tail, rh, rt, group, fused, region)
    meta: list[dict] = []

    for att in recipe.attachments:
        # (instance_id, origin, rot, mirror_flag, cross_parent_bone, phase)
        instances: list[tuple] = []

        rl = _euler(att.rotation)  # per-attachment pivot about the socket (no-op if 0)

        if att.parent is None:
            instances.append((att.id, np.zeros(3), rl, False, None, 0))
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
                    instances.append((f"{att.id}_{k}", origin, p.rot @ rk @ rl, False, cross, k))
            elif att.mirror:
                # right copy gets the Z-reflected rotation so the pair stays symmetric
                rl_r = _Z_REFLECT @ rl @ _Z_REFLECT
                for suffix, mir in (("_l", False), ("_r", True)):
                    parent_inst = att.parent if att.parent not in mirrored else f"{att.parent}_{'r' if mir else 'l'}"
                    p = placed[parent_inst]
                    sp = base.copy()
                    if mir:
                        sp[2] *= -1.0
                    origin = p.origin + p.rot @ sp
                    cross = f"{parent_inst}_{sock.host_bone}"
                    instances.append((f"{att.id}{suffix}", origin, p.rot @ (rl_r if mir else rl), mir, cross, 0))
            else:
                p = placed[att.parent]
                origin = p.origin + p.rot @ base
                cross = f"{att.parent}_{sock.host_bone}"
                instances.append((att.id, origin, p.rot @ rl, False, cross, 0))

        for inst_id, origin, rot, mir, cross, phase in instances:
            placed[inst_id] = _Placed(origin, rot, mir, att.module)
            meta.append({"id": inst_id, "kind": att.module.kind,
                         "local_bones": [b.name for b in att.module.bones], "phase": phase})
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
                            b.radius_head, b.radius_tail, b.group,
                            getattr(b, "fused", True), getattr(b, "region", None)))

    # Uniform height scale + ground clamp (matches v1 convention). Girth scales the
    # emitted *radius* only (not the clamp), so bone positions/weights/clips are
    # byte-identical across builds — girth is purely the SDF surface thickness.
    g = float(spec.proportions["heightCm"]) / _REF_HEIGHT_CM
    girth = spec.girth
    min_y = min(min(h[1] - rh, t[1] - rt) for _, _, h, t, rh, rt, _, _, _ in raw) * g

    bones: list[Bone] = []
    for name, parent, head, tail, rh, rt, group, fused, region in raw:
        head = head * g
        tail = tail * g
        head[1] -= min_y
        tail[1] -= min_y
        bones.append(
            Bone(name=name, parent=parent, head=head.astype(_F), tail=tail.astype(_F),
                 radius_head=float(rh * g * girth), radius_tail=float(rt * g * girth),
                 fused=fused, region=region)
        )
    return bones, meta


def assemble_recipe(recipe: Recipe, spec: Spec) -> list[Bone]:
    return assemble_with_meta(recipe, spec)[0]


def build_actor(recipe: Recipe, spec: Spec, rng: Rng) -> tuple[list[Bone], Mesh]:
    """Recipe → assembled skeleton → v1 geometry/skin/uv/paint (unchanged)."""
    skel = assemble_recipe(recipe, spec)
    mesh = build_geometry(skel, spec, rng, ())
    mesh = skin(mesh, skel)
    mesh = layout_uvs(mesh, skel, spec)
    mesh = paint_colors(mesh, skel, spec)
    return skel, mesh

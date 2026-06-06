"""Module library + preset recipes (v2).

V2-M0 ships the handful of skeletal modules the biped needs: spine, neck, head,
arm, leg. Each is authored in a local frame with its root at the origin; sockets
mark where children attach. The biped recipe composes them (arms/legs via the
``mirror`` flag). Limb-rich and radial modules (tail, tentacle, wing, fin, orb,
eyestalk) land in V2-M1.
"""

from __future__ import annotations

from .types import Attachment, BoneSpec, Module, Recipe, Socket, v


def spine_module() -> Module:
    return Module(
        kind="spine",
        bones=[
            BoneSpec("root", None, v(0, 0, 0), v(0, 0.08, 0), 0.075, 0.070, "spine"),
            BoneSpec("spine_01", "root", v(0, 0.08, 0), v(0, 0.16, 0), 0.070, 0.062, "spine"),
            BoneSpec("spine_02", "spine_01", v(0, 0.16, 0), v(0, 0.22, 0), 0.062, 0.050, "spine"),
        ],
        sockets={
            "neck": Socket("neck", v(0, 0.22, 0), "spine_02"),
            "shoulder": Socket("shoulder", v(0, 0.20, 0.07), "spine_02", mirror=True),
            "hip": Socket("hip", v(0, 0.005, 0.045), "root", mirror=True),
        },
    )


def neck_module() -> Module:
    return Module(
        kind="neck",
        bones=[BoneSpec("neck_01", None, v(0, 0, 0), v(0, 0.035, 0), 0.026, 0.024, "neck")],
        sockets={"top": Socket("top", v(0, 0.035, 0), "neck_01")},
    )


def head_module() -> Module:
    return Module(
        kind="head",
        bones=[BoneSpec("head", None, v(0, 0, 0), v(0, 0.055, 0), 0.052, 0.050, "head")],
        sockets={},
    )


def arm_module() -> Module:
    return Module(
        kind="arm",
        bones=[
            BoneSpec("upperarm", None, v(0, 0, 0), v(0, -0.13, 0.02), 0.032, 0.026, "arm"),
            BoneSpec("forearm", "upperarm", v(0, -0.13, 0.02), v(0, -0.25, 0.03), 0.026, 0.020, "arm"),
            BoneSpec("hand", "forearm", v(0, -0.25, 0.03), v(0, -0.30, 0.035), 0.022, 0.018, "arm"),
        ],
        sockets={},
    )


def leg_module() -> Module:
    return Module(
        kind="leg",
        bones=[
            BoneSpec("thigh", None, v(0, 0, 0), v(0, -0.15, 0.005), 0.038, 0.030, "leg"),
            BoneSpec("shin", "thigh", v(0, -0.15, 0.005), v(0, -0.28, 0.01), 0.030, 0.022, "leg"),
            BoneSpec("foot", "shin", v(0, -0.28, 0.01), v(0.07, -0.32, 0.01), 0.028, 0.022, "leg"),
        ],
        sockets={},
    )


def biped_recipe() -> Recipe:
    return Recipe(
        name="ModularBiped",
        attachments=[
            Attachment("spine", spine_module()),
            Attachment("neck", neck_module(), parent="spine", parent_socket="neck"),
            Attachment("head", head_module(), parent="neck", parent_socket="top"),
            Attachment("arm", arm_module(), parent="spine", parent_socket="shoulder", mirror=True),
            Attachment("leg", leg_module(), parent="spine", parent_socket="hip", mirror=True),
        ],
    )

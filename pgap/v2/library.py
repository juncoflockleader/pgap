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


# --------------------------------------------------------------------------- #
# V2-M1 modules: chain (tail/tentacle), orb body, eyeball, eyestalk.
# --------------------------------------------------------------------------- #
def _chain(kind: str, points, radii, group: str) -> Module:
    """A segment chain through ``points`` (local), radii per node. seg0 is root."""
    bones = []
    for i in range(len(points) - 1):
        bones.append(BoneSpec(
            f"seg_{i}", (f"seg_{i-1}" if i > 0 else None),
            points[i], points[i + 1], radii[i], radii[i + 1], group,
        ))
    return Module(kind=kind, bones=bones, sockets={})


def tentacle_module() -> Module:
    # Pointing outward (+X) and down (-Y), curling toward the tip.
    pts = [v(0, 0, 0), v(0.04, -0.06, 0), v(0.08, -0.13, 0), v(0.10, -0.20, 0),
           v(0.10, -0.27, 0), v(0.08, -0.33, 0), v(0.05, -0.38, 0)]
    radii = [0.030, 0.027, 0.023, 0.019, 0.015, 0.011, 0.008]
    return _chain("tentacle", pts, radii, "tentacle")


def orb_module(radius: float = 0.24, eye_ring: int = 8, arm_ring: int = 8) -> Module:
    """A near-spherical body (capsule with head≈tail, big radius) with a top
    ring (eyestalks), a front socket (central eye), and a bottom ring (arms)."""
    return Module(
        kind="orb",
        bones=[BoneSpec("orb", None, v(0, 0, 0), v(0, 0.004, 0), radius, radius, "body")],
        sockets={
            "eyes_ring": Socket("eyes_ring", v(0, radius * 0.62, 0), "orb",
                                ring=eye_ring, ring_radius=radius * 0.35),
            "front": Socket("front", v(radius * 0.85, 0, 0), "orb"),
            "arms_ring": Socket("arms_ring", v(0, -radius * 0.5, 0), "orb",
                                ring=arm_ring, ring_radius=radius * 0.55),
        },
    )


def eyeball_module(radius: float = 0.11) -> Module:
    return Module(
        kind="eye",
        bones=[BoneSpec("eye", None, v(0, 0, 0), v(0.004, 0, 0), radius, radius, "eye")],
        sockets={},
    )


def eyestalk_module(eye_radius: float = 0.05) -> Module:
    # Authored pointing outward (+X) and up (+Y); ring yaw aims it radially.
    return Module(
        kind="eyestalk",
        bones=[
            BoneSpec("stem1", None, v(0, 0, 0), v(0.05, 0.09, 0), 0.015, 0.012, "eyestalk"),
            BoneSpec("stem2", "stem1", v(0.05, 0.09, 0), v(0.09, 0.17, 0), 0.012, 0.010, "eyestalk"),
            BoneSpec("eye", "stem2", v(0.09, 0.17, 0), v(0.095, 0.175, 0), eye_radius, eye_radius, "eye"),
        ],
        sockets={},
    )


def beholder_recipe(eyes: int = 8) -> Recipe:
    return Recipe(
        name="Beholder",
        attachments=[
            Attachment("orb", orb_module(radius=0.24, eye_ring=eyes)),
            Attachment("eye", eyeball_module(0.11), parent="orb", parent_socket="front"),
            Attachment("stalk", eyestalk_module(), parent="orb", parent_socket="eyes_ring"),
        ],
    )


def kraken_recipe(arms: int = 8) -> Recipe:
    return Recipe(
        name="Kraken",
        attachments=[
            Attachment("mantle", orb_module(radius=0.18, arm_ring=arms)),
            Attachment("eye", eyeball_module(0.06), parent="mantle", parent_socket="front"),
            Attachment("arms", tentacle_module(), parent="mantle", parent_socket="arms_ring"),
        ],
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

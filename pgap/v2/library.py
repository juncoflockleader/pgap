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
            "base": Socket("base", v(0, -0.005, 0), "root"),  # centered (mermaid tail)
            "wings": Socket("wings", v(0, 0.18, 0.05), "spine_02", mirror=True),  # back (cthulhu)
        },
    )


def neck_module() -> Module:
    return Module(
        kind="neck",
        bones=[BoneSpec("neck_01", None, v(0, 0, 0), v(0, 0.035, 0), 0.026, 0.024, "neck")],
        sockets={
            "top": Socket("top", v(0, 0.035, 0), "neck_01"),
            "mane": Socket("mane", v(0, 0.02, 0), "neck_01"),
        },
    )


def head_module() -> Module:
    return Module(
        kind="head",
        bones=[BoneSpec("head", None, v(0, 0, 0), v(0, 0.055, 0), 0.052, 0.050, "head")],
        sockets={
            "horns": Socket("horns", v(0, 0.05, 0), "head"),
            "ears": Socket("ears", v(0, 0.04, 0), "head"),
            "tusks": Socket("tusks", v(0.03, 0.005, 0), "head"),
        },
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
        sockets={"tip": Socket("tip", v(0.07, -0.32, 0.01), "foot")},
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


# --------------------------------------------------------------------------- #
# V2-M1 (cont.): horizontal body, dragon neck/head, wing, fin, serpent tail.
# --------------------------------------------------------------------------- #
def body_module() -> Module:
    """A horizontal quadruped/dragon torso (+X forward). Sockets for neck, wings
    (top), fore/hind legs (underside), a rear ring (tail/tentacles), and a base."""
    return Module(
        kind="body",
        bones=[
            BoneSpec("spine0", None, v(0, 0, 0), v(0.25, 0.02, 0), 0.13, 0.13, "spine"),
            BoneSpec("spine1", "spine0", v(0.25, 0.02, 0), v(0.50, 0.0, 0), 0.13, 0.11, "spine"),
            BoneSpec("spine2", "spine1", v(0.50, 0.0, 0), v(0.70, 0.05, 0), 0.11, 0.09, "spine"),
        ],
        sockets={
            "neck": Socket("neck", v(0.70, 0.05, 0), "spine2"),
            "wings": Socket("wings", v(0.46, 0.12, 0.05), "spine1", mirror=True),
            "shoulder": Socket("shoulder", v(0.58, -0.06, 0.10), "spine2", mirror=True),
            "hip": Socket("hip", v(0.06, -0.06, 0.10), "spine0", mirror=True),
            "rear_ring": Socket("rear_ring", v(-0.02, -0.03, 0), "spine0", ring=6, ring_radius=0.07),
            "tail": Socket("tail", v(-0.02, 0.02, 0), "spine0"),
        },
    )


def dragon_neck_module() -> Module:
    return Module(
        kind="neck",
        bones=[
            BoneSpec("neck_0", None, v(0, 0, 0), v(0.08, 0.09, 0), 0.075, 0.060, "neck"),
            BoneSpec("neck_1", "neck_0", v(0.08, 0.09, 0), v(0.16, 0.17, 0), 0.060, 0.050, "neck"),
        ],
        sockets={
            "top": Socket("top", v(0.16, 0.17, 0), "neck_1"),
            "mane": Socket("mane", v(0.05, 0.06, 0), "neck_0"),
        },
    )


def draconic_head_module() -> Module:
    return Module(
        kind="head",
        bones=[
            BoneSpec("skull", None, v(0, 0, 0), v(0.10, 0.0, 0), 0.075, 0.065, "head"),
            BoneSpec("snout", "skull", v(0.10, 0.0, 0), v(0.24, -0.03, 0), 0.055, 0.030, "snout"),
            BoneSpec("horn_l", "skull", v(0.01, 0.05, 0.03), v(-0.06, 0.13, 0.05), 0.018, 0.006, "head"),
            BoneSpec("horn_r", "skull", v(0.01, 0.05, -0.03), v(-0.06, 0.13, -0.05), 0.018, 0.006, "head"),
        ],
        sockets={"horns": Socket("horns", v(0.02, 0.06, 0), "skull")},
    )


def wing_module() -> Module:
    """Stylized bat wing: an arm + 3 splayed fingers + webbing, swept up and out."""
    elbow = v(0, 0.13, 0.15)
    t1, t2, t3 = v(-0.10, 0.20, 0.26), v(0.02, 0.14, 0.34), v(0.13, 0.16, 0.24)
    return Module(
        kind="wing",
        bones=[
            BoneSpec("arm", None, v(0, 0, 0), elbow, 0.022, 0.016, "wing"),
            BoneSpec("f1", "arm", elbow, t1, 0.014, 0.005, "wing"),
            BoneSpec("f2", "arm", elbow, t2, 0.014, 0.005, "wing"),
            BoneSpec("f3", "arm", elbow, t3, 0.014, 0.005, "wing"),
            BoneSpec("web1", "f1", t1, t2, 0.006, 0.006, "wing"),
            BoneSpec("web2", "f2", t2, t3, 0.006, 0.006, "wing"),
        ],
        sockets={},
    )


def wing_feathered_module() -> Module:
    """Swan/angel wing: an arm + a fan of separated feather capsules (gaps so
    smooth-min keeps them distinct), swept up and out. No webbing."""
    elbow = v(0, 0.13, 0.15)
    tips = [v(-0.16, 0.20, 0.20), v(-0.07, 0.24, 0.29), v(0.03, 0.21, 0.37),
            v(0.12, 0.16, 0.34), v(0.19, 0.10, 0.25)]
    bones = [BoneSpec("arm", None, v(0, 0, 0), elbow, 0.022, 0.016, "wing")]
    for i, t in enumerate(tips):
        bones.append(BoneSpec(f"feather_{i}", "arm", elbow, t, 0.011, 0.004, "wing"))
    return Module(kind="wing", bones=bones, sockets={})


def wing_membrane_module() -> Module:
    """Glider/membrane wing: a stiff near-flat delta — leading edge + struts +
    trailing edge, thin, pointing out (+Z)."""
    le_tip = v(0, 0.06, 0.42)        # long straight leading edge, out + slight up
    inner = v(-0.14, -0.02, 0.10)    # trailing edge near the body
    mid = v(-0.16, 0.0, 0.26)        # trailing mid
    return Module(
        kind="wing",
        bones=[
            BoneSpec("le", None, v(0, 0, 0), le_tip, 0.020, 0.008, "wing"),
            BoneSpec("trail_in", "le", v(0, 0, 0), inner, 0.013, 0.008, "wing"),
            BoneSpec("trail_mid", "le", v(0, 0.03, 0.22), mid, 0.010, 0.007, "wing"),
            BoneSpec("tip", "le", le_tip, mid, 0.008, 0.006, "wing"),  # leading tip → trailing mid
            BoneSpec("web", "trail_mid", mid, inner, 0.008, 0.008, "wing"),
        ],
        sockets={},
    )


def wing_insect_module() -> Module:
    """Insect/fairy wing: two long thin lobes from a short arm, leaf-like."""
    base = v(0, 0.04, 0.14)
    return Module(
        kind="wing",
        bones=[
            BoneSpec("arm", None, v(0, 0, 0), base, 0.014, 0.010, "wing"),
            BoneSpec("upper", "arm", base, v(-0.05, 0.12, 0.42), 0.011, 0.004, "wing"),
            BoneSpec("lower", "arm", base, v(-0.03, -0.05, 0.36), 0.010, 0.004, "wing"),
            BoneSpec("vein", "arm", base, v(-0.04, 0.04, 0.40), 0.006, 0.004, "wing"),
        ],
        sockets={},
    )


def fin_module() -> Module:
    """A flat tail fluke (fan in the X/Z plane), pointing back/down from the tip."""
    base = v(0, 0, 0)
    a, b, c = v(-0.10, -0.04, 0.10), v(-0.14, -0.06, 0.0), v(-0.10, -0.04, -0.10)
    return Module(
        kind="fin",
        bones=[
            BoneSpec("lobe_l", None, base, a, 0.02, 0.006, "fin"),
            BoneSpec("mid", None, base, b, 0.02, 0.006, "fin"),
            BoneSpec("lobe_r", None, base, c, 0.02, 0.006, "fin"),
            BoneSpec("web_l", "lobe_l", a, b, 0.006, 0.006, "fin"),
            BoneSpec("web_r", "mid", b, c, 0.006, 0.006, "fin"),
        ],
        sockets={},
    )


def serpent_tail_module() -> Module:
    """A long tapering chain dropping down/back, with a fin socket at the tip."""
    pts = [v(0, 0, 0), v(-0.03, -0.12, 0), v(-0.04, -0.24, 0), v(-0.02, -0.35, 0),
           v(0.02, -0.45, 0), v(0.06, -0.53, 0)]
    radii = [0.085, 0.072, 0.058, 0.044, 0.030, 0.020]
    bones = [
        BoneSpec(f"seg_{i}", (f"seg_{i-1}" if i else None), pts[i], pts[i + 1],
                 radii[i], radii[i + 1], "tail")
        for i in range(len(pts) - 1)
    ]
    return Module(kind="tail", bones=bones, sockets={"tip": Socket("tip", pts[-1], f"seg_{len(pts)-2}")})


def octopus_dragon_recipe() -> Recipe:
    return Recipe(
        name="OctopusDragon",
        attachments=[
            Attachment("body", body_module()),
            Attachment("neck", dragon_neck_module(), parent="body", parent_socket="neck"),
            Attachment("head", draconic_head_module(), parent="neck", parent_socket="top"),
            Attachment("wing", wing_module(), parent="body", parent_socket="wings", mirror=True),
            Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
            Attachment("arms", tentacle_module(), parent="body", parent_socket="rear_ring"),
        ],
    )


def sphinx_recipe() -> Recipe:
    return Recipe(
        name="Sphinx",
        attachments=[
            Attachment("body", body_module()),
            Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
            Attachment("head", head_module(), parent="neck", parent_socket="top"),
            Attachment("wing", wing_module(), parent="body", parent_socket="wings", mirror=True),
            Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
            Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        ],
    )


def merfolk_recipe() -> Recipe:
    return Recipe(
        name="Merfolk",
        attachments=[
            Attachment("spine", spine_module()),
            Attachment("neck", neck_module(), parent="spine", parent_socket="neck"),
            Attachment("head", head_module(), parent="neck", parent_socket="top"),
            Attachment("arm", arm_module(), parent="spine", parent_socket="shoulder", mirror=True),
            Attachment("tail", serpent_tail_module(), parent="spine", parent_socket="base"),
            Attachment("fin", fin_module(), parent="tail", parent_socket="tip"),
        ],
    )


# --------------------------------------------------------------------------- #
# V3-M2: horn slot — variants attach at head.horns, pointing up (+Y).
# --------------------------------------------------------------------------- #
def _bilateral(segments) -> list:
    """Author a left side (z>=0); emit it (_l) plus a Z-mirrored twin (_r)."""
    out = []
    for side, sign in (("l", 1.0), ("r", -1.0)):
        for nm, par, h, t, rh, rt in segments:
            hh, tt = h.copy(), t.copy()
            hh[2] *= sign
            tt[2] *= sign
            out.append(BoneSpec(f"{nm}_{side}", (f"{par}_{side}" if par else None),
                                hh, tt, rh, rt, "horn"))
    return out


def horn_unicorn_module() -> Module:
    return Module("horn", [BoneSpec("horn", None, v(0, 0, 0), v(0.05, 0.26, 0), 0.024, 0.003, "horn")], {})


def horn_rhino_module() -> Module:
    return Module("horn", [BoneSpec("horn", None, v(0, 0, 0), v(0.16, 0.13, 0), 0.036, 0.006, "horn")], {})


def horn_antler_module() -> Module:
    seg = [
        ("beam", None, v(0, 0, 0.02), v(-0.03, 0.17, 0.08), 0.016, 0.008),
        ("tine1", "beam", v(-0.03, 0.17, 0.08), v(-0.10, 0.25, 0.05), 0.009, 0.003),
        ("tine2", "beam", v(-0.03, 0.17, 0.08), v(0.0, 0.24, 0.14), 0.009, 0.003),
    ]
    return Module("horn", _bilateral(seg), {})


def horn_ram_module() -> Module:
    seg = [
        ("c0", None, v(0, 0, 0.02), v(-0.05, 0.11, 0.07), 0.020, 0.014),
        ("c1", "c0", v(-0.05, 0.11, 0.07), v(-0.03, 0.16, 0.15), 0.014, 0.009),
        ("c2", "c1", v(-0.03, 0.16, 0.15), v(0.03, 0.09, 0.20), 0.009, 0.005),
    ]
    return Module("horn", _bilateral(seg), {})


def horn_bull_module() -> Module:
    seg = [
        ("b0", None, v(0, 0.02, 0.02), v(-0.10, 0.05, 0.12), 0.022, 0.012),
        ("b1", "b0", v(-0.10, 0.05, 0.12), v(-0.11, 0.19, 0.10), 0.012, 0.005),
    ]
    return Module("horn", _bilateral(seg), {})


def unicorn_recipe() -> Recipe:
    return Recipe(
        name="Unicorn",
        attachments=[
            Attachment("body", body_module()),
            Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
            Attachment("head", head_module(), parent="neck", parent_socket="top"),
            Attachment("horn", horn_unicorn_module(), parent="head", parent_socket="horns"),
            Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
            Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        ],
    )


def stag_recipe() -> Recipe:
    return Recipe(
        name="Stag",
        attachments=[
            Attachment("body", body_module()),
            Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
            Attachment("head", head_module(), parent="neck", parent_socket="top"),
            Attachment("antlers", horn_antler_module(), parent="head", parent_socket="horns"),
            Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
            Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        ],
    )


# --------------------------------------------------------------------------- #
# V3-M3: ears, tusks (head slots), hoof / claw (leg-tip), mane (neck ridge).
# --------------------------------------------------------------------------- #
def _ear(head, tail, rh, rt) -> Module:
    return Module("ear", _bilateral([("ear", None, head, tail, rh, rt)]), {})


def ear_floppy_module() -> Module:
    return _ear(v(0, 0, 0.03), v(0.02, -0.11, 0.06), 0.030, 0.014)


def ear_pointy_module() -> Module:
    return _ear(v(0, 0, 0.025), v(-0.01, 0.11, 0.04), 0.025, 0.005)


def ear_bat_module() -> Module:
    return _ear(v(0, 0, 0.03), v(0.0, 0.11, 0.10), 0.024, 0.004)


def ear_long_module() -> Module:
    return _ear(v(0, 0, 0.025), v(0.03, -0.17, 0.05), 0.026, 0.010)


def tusk_boar_module() -> Module:
    return Module("tusk", _bilateral([
        ("t0", None, v(0, 0, 0.025), v(0.04, 0.03, 0.04), 0.013, 0.008),
        ("t1", "t0", v(0.04, 0.03, 0.04), v(0.06, 0.10, 0.04), 0.008, 0.003),
    ]), {})


def tusk_elephant_module() -> Module:
    return Module("tusk", _bilateral([
        ("t", None, v(0, 0, 0.02), v(0.22, -0.06, 0.03), 0.020, 0.005),
    ]), {})


def tusk_walrus_module() -> Module:
    return Module("tusk", _bilateral([
        ("t", None, v(0, 0, 0.02), v(0.02, -0.18, 0.03), 0.016, 0.005),
    ]), {})


def hoof_module() -> Module:
    return Module("hoof", [BoneSpec("hoof", None, v(0, 0, 0), v(0.04, -0.02, 0), 0.036, 0.032, "hoof")], {})


def claw_module() -> Module:
    return Module("claw", [
        BoneSpec("c0", None, v(0, 0, 0), v(0.05, -0.02, 0.025), 0.010, 0.003, "claw"),
        BoneSpec("c1", None, v(0, 0, 0), v(0.06, -0.02, 0.0), 0.010, 0.003, "claw"),
        BoneSpec("c2", None, v(0, 0, 0), v(0.05, -0.02, -0.025), 0.010, 0.003, "claw"),
    ], {})


def mane_module() -> Module:
    return Module("mane", [
        BoneSpec("m0", None, v(0.00, 0, 0), v(-0.05, 0.08, 0), 0.022, 0.008, "mane"),
        BoneSpec("m1", None, v(0.03, 0, 0), v(-0.03, 0.09, 0), 0.020, 0.007, "mane"),
        BoneSpec("m2", None, v(0.06, 0, 0), v(-0.01, 0.08, 0), 0.018, 0.006, "mane"),
    ], {})


def boar_recipe() -> Recipe:
    return Recipe("Boar", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        Attachment("tusks", tusk_boar_module(), parent="head", parent_socket="tusks"),
        Attachment("ears", ear_pointy_module(), parent="head", parent_socket="ears"),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
    ])


def horse_recipe() -> Recipe:
    return Recipe("Horse", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        Attachment("ears", ear_pointy_module(), parent="head", parent_socket="ears"),
        Attachment("mane", mane_module(), parent="neck", parent_socket="mane"),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("forehoof", hoof_module(), parent="foreleg", parent_socket="tip", mirror=True),
        Attachment("hindhoof", hoof_module(), parent="hindleg", parent_socket="tip", mirror=True),
    ])


def feline_recipe() -> Recipe:
    return Recipe("Feline", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        Attachment("ears", ear_pointy_module(), parent="head", parent_socket="ears"),
        Attachment("mane", mane_module(), parent="neck", parent_socket="mane"),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("foreclaw", claw_module(), parent="foreleg", parent_socket="tip", mirror=True),
        Attachment("hindclaw", claw_module(), parent="hindleg", parent_socket="tip", mirror=True),
    ])


def cephalopod_head_module() -> Module:
    """A rounded skull with a downward-front ring of face tentacles (cthulhu)."""
    return Module(
        kind="head",
        bones=[BoneSpec("skull", None, v(0, 0, 0), v(0.05, 0.0, 0), 0.065, 0.060, "head")],
        sockets={
            "face": Socket("face", v(0.05, -0.02, 0), "skull", ring=6, ring_radius=0.025),
            "horns": Socket("horns", v(0.0, 0.05, 0), "skull"),
        },
    )


def cthulhu_recipe() -> Recipe:
    return Recipe(
        name="Cthulhu",
        attachments=[
            Attachment("spine", spine_module()),
            Attachment("neck", neck_module(), parent="spine", parent_socket="neck"),
            Attachment("head", cephalopod_head_module(), parent="neck", parent_socket="top"),
            Attachment("arm", arm_module(), parent="spine", parent_socket="shoulder", mirror=True),
            Attachment("leg", leg_module(), parent="spine", parent_socket="hip", mirror=True),
            Attachment("wing", wing_module(), parent="spine", parent_socket="wings", mirror=True),
            Attachment("face", tentacle_module(), parent="head", parent_socket="face"),
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

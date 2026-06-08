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
            "eyes": Socket("eyes", v(0.034, 0.030, 0), "head"),
            "jaws": Socket("jaws", v(0.044, -0.006, 0), "head"),
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
        bones=[BoneSpec("eye", None, v(0, 0, 0), v(0.004, 0, 0), radius, radius, "eye",
                        region="eyes")],
        sockets={},
    )


def eyestalk_module(eye_radius: float = 0.05) -> Module:
    # Authored pointing outward (+X) and up (+Y); ring yaw aims it radially.
    return Module(
        kind="eyestalk",
        bones=[
            BoneSpec("stem1", None, v(0, 0, 0), v(0.05, 0.09, 0), 0.015, 0.012, "eyestalk"),
            BoneSpec("stem2", "stem1", v(0.05, 0.09, 0), v(0.09, 0.17, 0), 0.012, 0.010, "eyestalk"),
            BoneSpec("eye", "stem2", v(0.09, 0.17, 0), v(0.095, 0.175, 0), eye_radius, eye_radius, "eye",
                     region="eyes"),
        ],
        sockets={},
    )


def _eye_pair(segments) -> list:
    """Author a LEFT eye (z>0); emit it (_l) plus a Z-mirrored twin (_r). Every
    bone is non-fused (a proud bead, not melted in) and tagged region ``eyes`` so
    paint colors it the dark iris independent of the head coat. Mirrors ``_bilateral``
    but for the eye organ; used by :func:`eyes_module`."""
    out = []
    for side, sign in (("l", 1.0), ("r", -1.0)):
        for nm, par, h, t, rh, rt in segments:
            hh, tt = h.copy(), t.copy()
            hh[2] *= sign
            tt[2] *= sign
            out.append(BoneSpec(f"{nm}_{side}", (f"{par}_{side}" if par else None),
                                hh, tt, rh, rt, "eye", fused=False, region="eyes"))
    return out


def eyes_module(variant: str = "round", radius: float = 0.016,
                spacing: float = 0.030) -> Module:
    """A mirrored pair of proud eyeballs for a head's ``eyes`` socket.

    Authored in the head's local frame (+X forward, +Y up, +Z = left side): the
    socket sits at the front-upper face, and each eye sits ``spacing`` to its side,
    nudged slightly forward so the bead pokes proud of the skull. ``variant`` sets
    the bead shape; ``radius``/``spacing`` scale it to the head.

    Variants: ``round`` (a sphere — the default), ``almond`` (a horizontal capsule,
    wider than tall), ``slit`` (a narrow vertical capsule — reptilian). Pupil/iris
    detail is a texture-side upgrade (roadmap 1); here the dark ``eyes`` region
    reads as the pupil-forward eye from every angle.
    """
    fwd = 0.004  # nudge toward +X so the bead sits on the front of the face
    if variant == "round":
        seg = [("eye", None, v(fwd, 0.0, spacing), v(fwd + 0.002, 0.0, spacing),
                radius, radius)]
    elif variant == "almond":
        e = radius * 0.85
        seg = [("eye", None, v(fwd - radius, 0.0, spacing), v(fwd + radius, 0.0, spacing),
                e, e)]
    elif variant == "slit":
        e = radius * 0.80
        seg = [("eye", None, v(fwd, -radius, spacing), v(fwd, radius, spacing), e, e)]
    else:
        raise ValueError(f"unknown eyes variant {variant!r}")
    return Module(kind="eyes", bones=_eye_pair(seg), sockets={})


def jaws_module(radius: float = 0.013, width: float = 0.020, nose: bool = True) -> Module:
    """A static muzzle for a head's ``jaws`` socket: a proud black **nose** bead
    (non-fused, region ``nose``) above a dark **mouth line** (a thin *fused*
    capsule, region ``mouth``, that tints the lip without bulging the silhouette).

    Authored in the head's local frame (+X forward, +Y up, +Z = left side): the
    socket sits at the front-lower face, the nose pokes forward and up, the mouth
    runs side-to-side just below it. ``radius`` scales the nose (the mouth is a
    fraction of it); ``width`` is the half-length of the lip line; ``nose=False``
    drops the nose for beaked/lipped faces. Mirrors the v1 dog's jaws on the bone
    path, reusing the same ``fused``/``region`` capability as :func:`eyes_module`.
    """
    bones = []
    if nose:
        bones.append(BoneSpec("nose", None, v(0.006, 0.009, 0), v(0.008, 0.009, 0),
                              radius, radius, "nose", fused=False, region="nose"))
    rm = radius * 0.45
    bones.append(BoneSpec("mouth", None, v(-0.001, -0.006, width), v(-0.001, -0.006, -width),
                          rm, rm, "mouth", region="mouth"))
    return Module(kind="jaws", bones=bones, sockets={})


def _eyes_for(parent: str, variant: str = "round", radius: float = 0.016,
              spacing: float = 0.030, aid: str = "eyes") -> "Attachment":
    """A standard eyes attachment onto ``parent``'s ``eyes`` socket. Used by every
    head-bearing preset so creatures actually have a face. ``aid`` overrides the
    attachment id so multi-headed creatures (hydra) get unique ids."""
    return Attachment(aid, eyes_module(variant, radius, spacing),
                      parent=parent, parent_socket="eyes")


def _jaws_for(parent: str, radius: float = 0.013, width: float = 0.020,
              nose: bool = True, aid: str = "jaws") -> "Attachment":
    """A standard jaws (nose + mouth line) attachment onto ``parent``'s ``jaws``
    socket — paired with :func:`_eyes_for` so head-bearing presets read as faces.
    ``aid`` overrides the attachment id (unique faces on multi-headed creatures)."""
    return Attachment(aid, jaws_module(radius, width, nose),
                      parent=parent, parent_socket="jaws")


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
        ],  # horns are their own slot now (V3) — attach via head.horns
        sockets={
            "horns": Socket("horns", v(0.02, 0.06, 0), "skull"),
            "ears": Socket("ears", v(-0.02, 0.05, 0), "skull"),
            "tusks": Socket("tusks", v(0.20, -0.04, 0), "snout"),
            "eyes": Socket("eyes", v(0.075, 0.045, 0), "skull"),
            "jaws": Socket("jaws", v(0.235, -0.030, 0), "snout"),
        },
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
            Attachment("horns", horn_bull_module(), parent="head", parent_socket="horns"),
            _eyes_for("head", "slit", radius=0.020, spacing=0.045),
            _jaws_for("head", radius=0.020, width=0.035),
            Attachment("wing", wing_module(), parent="body", parent_socket="wings", mirror=True),
            Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
            Attachment("arms", tentacle_module(), parent="body", parent_socket="rear_ring"),
        ],
    )


def dragon_recipe() -> Recipe:
    """A classic dragon, now expressible from the variant library."""
    return Recipe("Dragon", [
        Attachment("body", body_module()),
        Attachment("neck", dragon_neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", draconic_head_module(), parent="neck", parent_socket="top"),
        Attachment("horns", horn_bull_module(), parent="head", parent_socket="horns"),
        _eyes_for("head", "slit", radius=0.020, spacing=0.045),
        _jaws_for("head", radius=0.020, width=0.035),
        Attachment("wing", wing_module(), parent="body", parent_socket="wings", mirror=True),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])


def sphinx_recipe() -> Recipe:
    return Recipe(
        name="Sphinx",
        attachments=[
            Attachment("body", body_module()),
            Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
            Attachment("head", head_module(), parent="neck", parent_socket="top"),
            _eyes_for("head"),
            _jaws_for("head"),
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
            _eyes_for("head"),
            _jaws_for("head"),
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
            _eyes_for("head"),
            _jaws_for("head"),
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
            _eyes_for("head"),
            _jaws_for("head"),
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
        _eyes_for("head"),
        _jaws_for("head"),
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
        _eyes_for("head"),
        _jaws_for("head"),
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
        _eyes_for("head"),
        _jaws_for("head"),
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
            "ears": Socket("ears", v(-0.02, 0.05, 0), "skull"),
            "tusks": Socket("tusks", v(0.05, -0.03, 0), "skull"),
            "eyes": Socket("eyes", v(0.050, 0.030, 0), "skull"),
            "jaws": Socket("jaws", v(0.058, -0.034, 0), "skull"),
        },
    )


def cthulhu_recipe() -> Recipe:
    return Recipe(
        name="Cthulhu",
        attachments=[
            Attachment("spine", spine_module()),
            Attachment("neck", neck_module(), parent="spine", parent_socket="neck"),
            Attachment("head", cephalopod_head_module(), parent="neck", parent_socket="top"),
            _eyes_for("head", radius=0.017, spacing=0.035),
            _jaws_for("head", radius=0.016, width=0.028),
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
            _eyes_for("head"),
            _jaws_for("head"),
            Attachment("arm", arm_module(), parent="spine", parent_socket="shoulder", mirror=True),
            Attachment("leg", leg_module(), parent="spine", parent_socket="hip", mirror=True),
        ],
    )


# --------------------------------------------------------------------------- #
# New body-plan archetypes (legless serpent, avian, arachnid)
# --------------------------------------------------------------------------- #
def serpent_body_module() -> Module:
    """A long legless body along +X that rises at the head end (cobra-like) and
    tapers to a thin tail. Exposes ``neck`` at the raised front for a head."""
    pts = [v(0.0, 0.0, 0.0), v(0.20, 0.0, 0.0), v(0.42, 0.0, 0.0),
           v(0.62, 0.04, 0.0), v(0.78, 0.16, 0.0), v(0.88, 0.30, 0.0)]
    radii = [0.030, 0.070, 0.082, 0.075, 0.058, 0.044]
    bones = [
        BoneSpec(f"coil_{i}", (f"coil_{i-1}" if i else None), pts[i], pts[i + 1],
                 radii[i], radii[i + 1], "spine")
        for i in range(len(pts) - 1)
    ]
    return Module(kind="serpent_body", bones=bones, sockets={
        "neck": Socket("neck", pts[-1], f"coil_{len(pts)-2}"),
    })


def serpent_recipe() -> Recipe:
    return Recipe("Serpent", [
        Attachment("body", serpent_body_module()),
        Attachment("head", head_module(), parent="body", parent_socket="neck"),
        _eyes_for("head", "slit"),
        _jaws_for("head"),
    ])


def avian_torso_module() -> Module:
    """A plump bird torso (+X = head end, +Y up): neck (front-top), wings
    (sides-top, bilateral), legs (underside, bilateral), tail (rear)."""
    bones = [
        BoneSpec("chest", None, v(0.0, 0.0, 0.0), v(-0.14, 0.0, 0.0), 0.11, 0.10, "spine"),
        BoneSpec("rump", "chest", v(-0.14, 0.0, 0.0), v(-0.28, 0.03, 0.0), 0.10, 0.07, "spine"),
    ]
    return Module(kind="avian_torso", bones=bones, sockets={
        "neck": Socket("neck", v(0.01, 0.08, 0.0), "chest"),
        "wings": Socket("wings", v(-0.07, 0.09, 0.05), "chest", mirror=True),
        "hip": Socket("hip", v(-0.13, -0.08, 0.05), "rump", mirror=True),
        "tail": Socket("tail", v(-0.28, 0.04, 0.0), "rump"),
    })


def avian_recipe() -> Recipe:
    return Recipe("Avian", [
        Attachment("torso", avian_torso_module()),
        Attachment("neck", neck_module(), parent="torso", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head", nose=False),
        Attachment("wing", wing_feathered_module(), parent="torso", parent_socket="wings", mirror=True),
        Attachment("leg", leg_module(), parent="torso", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="torso", parent_socket="tail"),
    ])


def arachnid_body_module(legs: int = 8) -> Module:
    """A spider: small cephalothorax at the origin + a fat abdomen behind (-X),
    with a ring of `legs` sockets for radial legs."""
    bones = [
        BoneSpec("cephalothorax", None, v(0.0, 0.0, 0.0), v(0.03, 0.0, 0.0), 0.10, 0.10, "body"),
        BoneSpec("abdomen", "cephalothorax", v(-0.07, 0.01, 0.0), v(-0.24, 0.05, 0.0), 0.13, 0.09, "body"),
    ]
    return Module(kind="arachnid_body", bones=bones, sockets={
        "legs_ring": Socket("legs_ring", v(0.0, 0.0, 0.0), "cephalothorax",
                            ring=legs, ring_radius=0.07),
        "head": Socket("head", v(0.10, 0.0, 0.0), "cephalothorax"),
        "eyes": Socket("eyes", v(0.085, 0.055, 0), "cephalothorax"),
    })


def spider_leg_module() -> Module:
    """A bent spider leg: out (+X) to a raised knee, then down to a foot. On a ring
    socket each copy is rotated around Y, so eight of them splay radially."""
    return Module(kind="spider_leg", bones=[
        BoneSpec("coxa", None, v(0, 0, 0), v(0.12, 0.03, 0), 0.024, 0.018, "leg"),
        BoneSpec("femur", "coxa", v(0.12, 0.03, 0), v(0.24, 0.06, 0), 0.018, 0.014, "leg"),
        BoneSpec("tibia", "femur", v(0.24, 0.06, 0), v(0.30, -0.18, 0), 0.014, 0.010, "leg"),
    ], sockets={})


def arachnid_recipe(legs: int = 8) -> Recipe:
    return Recipe("Arachnid", [
        Attachment("body", arachnid_body_module(legs)),
        Attachment("legs", spider_leg_module(), parent="body", parent_socket="legs_ring"),
        _eyes_for("body", radius=0.018, spacing=0.030),
    ])


# --------------------------------------------------------------------------- #
# More body-plan archetypes (hexapod / insect, centaur)
# --------------------------------------------------------------------------- #
def hexapod_body_module() -> Module:
    """An insect body along +X: abdomen (rear) — thorax (mid, the root) — head
    (front). Eyes/jaws on the head; three bilateral leg sockets (fore/mid/hind)
    along the thorax underside; an optional wings socket on the thorax top."""
    bones = [
        BoneSpec("thorax", None, v(0.0, 0.0, 0.0), v(0.12, 0.0, 0.0), 0.060, 0.052, "body"),
        BoneSpec("head", "thorax", v(0.12, 0.0, 0.0), v(0.22, 0.0, 0.0), 0.052, 0.042, "head"),
        BoneSpec("abdomen", "thorax", v(0.0, 0.0, 0.0), v(-0.20, 0.03, 0.0), 0.070, 0.040, "body"),
    ]
    return Module(kind="hexapod_body", bones=bones, sockets={
        "foreleg": Socket("foreleg", v(0.11, -0.02, 0.05), "thorax", mirror=True),
        "midleg": Socket("midleg", v(0.05, -0.03, 0.05), "thorax", mirror=True),
        "hindleg": Socket("hindleg", v(-0.01, -0.02, 0.05), "thorax", mirror=True),
        "wings": Socket("wings", v(0.02, 0.06, 0.03), "thorax", mirror=True),
        "eyes": Socket("eyes", v(0.205, 0.030, 0), "head"),
        "jaws": Socket("jaws", v(0.215, -0.020, 0), "head"),
    })


def insect_leg_module() -> Module:
    """A long bent insect leg authored out to the +Z side and down: the coxa/femur
    reach out to a high knee, the tibia drops steeply to the foot. Thin so it reads
    as a distinct leg, not part of the body. Mirror gives the right-side leg (three
    pairs splay a hexapod well clear of the thorax)."""
    return Module(kind="insect_leg", bones=[
        BoneSpec("coxa", None, v(0, 0, 0), v(0.0, 0.03, 0.16), 0.020, 0.015, "leg"),
        BoneSpec("femur", "coxa", v(0.0, 0.03, 0.16), v(0.0, 0.05, 0.32), 0.015, 0.011, "leg"),
        BoneSpec("tibia", "femur", v(0.0, 0.05, 0.32), v(0.0, -0.24, 0.38), 0.012, 0.008, "leg"),
    ], sockets={})


def hexapod_recipe() -> Recipe:
    return Recipe("Hexapod", [
        Attachment("body", hexapod_body_module()),
        _eyes_for("body", radius=0.014, spacing=0.024),
        _jaws_for("body", radius=0.012, width=0.016),
        Attachment("foreleg", insect_leg_module(), parent="body", parent_socket="foreleg", mirror=True),
        Attachment("midleg", insect_leg_module(), parent="body", parent_socket="midleg", mirror=True),
        Attachment("hindleg", insect_leg_module(), parent="body", parent_socket="hindleg", mirror=True),
    ])


def centaur_torso_module() -> Module:
    """A tall humanoid upper body (a taller `spine`) that rises +Y from the front of
    a quadruped body, so the human half clearly reads above the horse back. Exposes
    a top `neck` and bilateral `shoulder`s for the arms."""
    return Module(kind="centaur_torso", bones=[
        BoneSpec("pelvis", None, v(0, 0, 0), v(0, 0.13, 0), 0.085, 0.080, "spine"),
        BoneSpec("spine_01", "pelvis", v(0, 0.13, 0), v(0, 0.26, 0), 0.080, 0.070, "spine"),
        BoneSpec("spine_02", "spine_01", v(0, 0.26, 0), v(0, 0.38, 0), 0.070, 0.058, "spine"),
    ], sockets={
        "neck": Socket("neck", v(0, 0.38, 0), "spine_02"),
        "shoulder": Socket("shoulder", v(0, 0.34, 0.085), "spine_02", mirror=True),
    })


def hydra_neck_module() -> Module:
    """A tall S-neck (rises ~0.36, twice ``dragon_neck``) so a hydra's heads lift
    well clear of the body and fan apart instead of bunching at the shoulders."""
    return Module(kind="hydra_neck", bones=[
        BoneSpec("neck_0", None, v(0, 0, 0), v(0.05, 0.12, 0), 0.060, 0.052, "neck"),
        BoneSpec("neck_1", "neck_0", v(0.05, 0.12, 0), v(0.10, 0.24, 0), 0.052, 0.044, "neck"),
        BoneSpec("neck_2", "neck_1", v(0.10, 0.24, 0), v(0.15, 0.36, 0), 0.044, 0.038, "neck"),
    ], sockets={"top": Socket("top", v(0.15, 0.36, 0), "neck_2")})


def hydra_body_module() -> Module:
    """A dragon torso whose front carries *three* neck sockets (center + a raised
    bilateral pair) so a hydra can grow three necks/heads from one body."""
    bones = [
        BoneSpec("spine0", None, v(0, 0, 0), v(0.25, 0.02, 0), 0.13, 0.13, "spine"),
        BoneSpec("spine1", "spine0", v(0.25, 0.02, 0), v(0.50, 0.0, 0), 0.13, 0.11, "spine"),
        BoneSpec("spine2", "spine1", v(0.50, 0.0, 0), v(0.70, 0.05, 0), 0.11, 0.09, "spine"),
    ]
    return Module(kind="hydra_body", bones=bones, sockets={
        "neck_c": Socket("neck_c", v(0.70, 0.07, 0.0), "spine2"),
        "neck_l": Socket("neck_l", v(0.64, 0.05, 0.11), "spine2"),
        "neck_r": Socket("neck_r", v(0.64, 0.05, -0.11), "spine2"),
        "shoulder": Socket("shoulder", v(0.58, -0.06, 0.10), "spine2", mirror=True),
        "hip": Socket("hip", v(0.06, -0.06, 0.10), "spine0", mirror=True),
        "tail": Socket("tail", v(-0.02, 0.02, 0), "spine0"),
    })


# --------------------------------------------------------------------------- #
# L4 — named presets, each composed from the existing bases + parts.
# --------------------------------------------------------------------------- #
def griffin_recipe() -> Recipe:
    """Eagle head + feathered wings + front talons on a lion body."""
    return Recipe("Griffin", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head", nose=False),  # a beak
        Attachment("wing", wing_feathered_module(), parent="body", parent_socket="wings", mirror=True),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("talon", claw_module(), parent="foreleg", parent_socket="tip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])


def manticore_recipe() -> Recipe:
    """Human face + mane + bat wings + a spiked (serpent) tail on a lion body."""
    return Recipe("Manticore", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head"),
        Attachment("mane", mane_module(), parent="neck", parent_socket="mane"),
        Attachment("wing", wing_module(), parent="body", parent_socket="wings", mirror=True),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])


def wyvern_recipe() -> Recipe:
    """A two-legged dragon: wings + a single pair of (hind) legs + a draconic head."""
    return Recipe("Wyvern", [
        Attachment("body", body_module()),
        Attachment("neck", dragon_neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", draconic_head_module(), parent="neck", parent_socket="top"),
        Attachment("horns", horn_bull_module(), parent="head", parent_socket="horns"),
        _eyes_for("head", "slit", radius=0.020, spacing=0.045),
        _jaws_for("head", radius=0.020, width=0.035),
        Attachment("wing", wing_module(), parent="body", parent_socket="wings", mirror=True),
        Attachment("leg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])


def pegasus_recipe() -> Recipe:
    """A winged horse: feathered wings + hooves + mane."""
    return Recipe("Pegasus", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head"),
        Attachment("ears", ear_pointy_module(), parent="head", parent_socket="ears"),
        Attachment("mane", mane_module(), parent="neck", parent_socket="mane"),
        Attachment("wing", wing_feathered_module(), parent="body", parent_socket="wings", mirror=True),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("forehoof", hoof_module(), parent="foreleg", parent_socket="tip", mirror=True),
        Attachment("hindhoof", hoof_module(), parent="hindleg", parent_socket="tip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])


def hydra_recipe() -> Recipe:
    """Three serpentine necks + draconic heads on a dragon body."""
    atts = [Attachment("body", hydra_body_module())]
    for s, sock in (("c", "neck_c"), ("l", "neck_l"), ("r", "neck_r")):
        atts += [
            Attachment(f"neck_{s}", hydra_neck_module(), parent="body", parent_socket=sock),
            Attachment(f"head_{s}", draconic_head_module(), parent=f"neck_{s}", parent_socket="top"),
            _eyes_for(f"head_{s}", "slit", radius=0.018, spacing=0.040, aid=f"eyes_{s}"),
            _jaws_for(f"head_{s}", radius=0.018, width=0.030, aid=f"jaws_{s}"),
        ]
    atts += [
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ]
    return Recipe("Hydra", atts)


def naga_recipe() -> Recipe:
    """A humanoid upper body on a long serpent tail (snake-tailed, no fin)."""
    return Recipe("Naga", [
        Attachment("spine", spine_module()),
        Attachment("neck", neck_module(), parent="spine", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head", "slit"),
        _jaws_for("head"),
        Attachment("arm", arm_module(), parent="spine", parent_socket="shoulder", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="spine", parent_socket="base"),
    ])


def phoenix_recipe() -> Recipe:
    """A grand bird: feathered wings, a crest, and a long plumed tail."""
    return Recipe("Phoenix", [
        Attachment("torso", avian_torso_module()),
        Attachment("neck", neck_module(), parent="torso", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head", nose=False),  # beak
        Attachment("crest", horn_unicorn_module(), parent="head", parent_socket="horns"),
        Attachment("wing", wing_feathered_module(), parent="torso", parent_socket="wings", mirror=True),
        Attachment("leg", leg_module(), parent="torso", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="torso", parent_socket="tail"),
    ])


def basilisk_recipe() -> Recipe:
    """A serpent with a crest (crown) — the king of snakes."""
    return Recipe("Basilisk", [
        Attachment("body", serpent_body_module()),
        Attachment("head", draconic_head_module(), parent="body", parent_socket="neck"),
        Attachment("crest", horn_antler_module(), parent="head", parent_socket="horns"),
        _eyes_for("head", "slit", radius=0.020, spacing=0.045),
        _jaws_for("head", radius=0.020, width=0.035),
    ])


def chimera_recipe() -> Recipe:
    """A lion body with a maned head, goat (ram) horns, and a serpent tail."""
    return Recipe("Chimera", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head"),
        Attachment("horns", horn_ram_module(), parent="head", parent_socket="horns"),
        Attachment("mane", mane_module(), parent="neck", parent_socket="mane"),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])


def centaur_recipe() -> Recipe:
    """A quadruped body with a tall humanoid torso rising at the front: the vertical
    `centaur_torso` plugs into the horizontal `body`'s neck socket and rises,
    carrying the neck/head (+ eyes/jaws) and a pair of arms; the four legs and a
    tail hang off the horse body as usual."""
    return Recipe("Centaur", [
        Attachment("body", body_module()),
        Attachment("torso", centaur_torso_module(), parent="body", parent_socket="neck"),
        Attachment("neck", neck_module(), parent="torso", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"),
        _jaws_for("head"),
        Attachment("arm", arm_module(), parent="torso", parent_socket="shoulder", mirror=True),
        Attachment("foreleg", leg_module(), parent="body", parent_socket="shoulder", mirror=True),
        Attachment("hindleg", leg_module(), parent="body", parent_socket="hip", mirror=True),
        Attachment("tail", serpent_tail_module(), parent="body", parent_socket="tail"),
    ])

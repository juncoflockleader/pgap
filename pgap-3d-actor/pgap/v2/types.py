"""Module / socket / recipe data model (v2 core).

A creature is a graph of socketed modules. A ``Module`` carries its rig in a local
frame (root at the origin) plus the sockets it exposes. A ``Recipe`` is an ordered
list of ``Attachment``\\s (root first) that plug modules into each other's sockets.

V2-M0 scope: bones + sockets + mirror expansion. Module geometry parts, radial
(ring) sockets, per-module animation, and arbitrary socket orientation arrive in
later v2 milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


def v(x: float, y: float, z: float) -> np.ndarray:
    return np.array([x, y, z], dtype=np.float64)


@dataclass(frozen=True)
class BoneSpec:
    """A bone in the module's local frame (root attaches at local origin)."""

    name: str
    parent: Optional[str]  # local bone name, or None = module root
    head: np.ndarray
    tail: np.ndarray
    radius_head: float
    radius_tail: float
    group: str = "none"
    fused: bool = True            # False = proud, non-melting organ (e.g. eyeball)
    region: Optional[str] = None  # paint region override (e.g. "eyes")


@dataclass(frozen=True)
class Socket:
    """A named attach point a module exposes (local frame)."""

    name: str
    position: np.ndarray  # local
    host_bone: str        # the module bone this socket sits on (for parenting)
    mirror: bool = False  # informational; mirroring is driven by the Attachment
    ring: Optional[int] = None  # radial copies around the socket (V2-M1)
    ring_radius: float = 0.0    # circle radius for ring placement


@dataclass(frozen=True)
class Module:
    kind: str
    bones: list  # list[BoneSpec], root-first
    sockets: dict = field(default_factory=dict)  # name -> Socket


@dataclass(frozen=True)
class Attachment:
    """Plug ``module`` into ``parent``'s ``parent_socket``.

    ``mirror=True`` instantiates a bilateral pair (``<id>_l`` / ``<id>_r``); the
    ``_r`` instance is reflected across the Z axis.
    """

    id: str
    module: Module
    parent: Optional[str] = None       # attachment id of the host, or None = root
    parent_socket: Optional[str] = None
    mirror: bool = False


@dataclass(frozen=True)
class Recipe:
    name: str
    attachments: list  # list[Attachment], topologically sorted (root first)

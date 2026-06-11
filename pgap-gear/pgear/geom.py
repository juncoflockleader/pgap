"""Low-poly rigid-mesh kernel for gear.

Gear is hard-edged (blades, hafts, plates), so — unlike the SDF/marching-cubes
creatures in pgap-3d-actor — we build it from explicit flat-shaded primitives and
concatenate them. A :class:`MeshBuilder` accumulates triangles tagged by *material
id*; ``build()`` returns one indexed mesh. Pure numpy, deterministic. Frame: the
item runs along **+Y** (a sword points up), thickness on Z, width on X.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

_F = np.float32


class MeshBuilder:
    """Accumulates flat-shaded primitives, each tagged with a material id."""

    def __init__(self) -> None:
        self._pos: List[np.ndarray] = []
        self._nrm: List[np.ndarray] = []
        self._tris: List[Tuple[int, int, int]] = []
        self._tri_mat: List[int] = []

    def _quad(self, v0, v1, v2, v3, mat: int, ref) -> None:
        """Add a quad as 2 triangles, normal auto-oriented away from ``ref`` point."""
        v0, v1, v2, v3 = (np.asarray(v, float) for v in (v0, v1, v2, v3))
        n = np.cross(v1 - v0, v2 - v0)
        if np.dot(n, (v0 + v1 + v2 + v3) / 4.0 - np.asarray(ref, float)) < 0:
            v1, v3 = v3, v1                       # flip winding to face outward
        n = np.cross(v1 - v0, v2 - v0)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            return
        n = n / ln
        b = len(self._pos)
        self._pos.extend([v0, v1, v2, v3])
        self._nrm.extend([n, n, n, n])
        self._tris.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])
        self._tri_mat.extend([mat, mat])

    def _tri(self, v0, v1, v2, mat: int, ref) -> None:
        v0, v1, v2 = (np.asarray(v, float) for v in (v0, v1, v2))
        n = np.cross(v1 - v0, v2 - v0)
        if np.dot(n, (v0 + v1 + v2) / 3.0 - np.asarray(ref, float)) < 0:
            v1, v2 = v2, v1
        n = np.cross(v1 - v0, v2 - v0)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            return
        n = n / ln
        b = len(self._pos)
        self._pos.extend([v0, v1, v2])
        self._nrm.extend([n, n, n])
        self._tris.append((b, b + 1, b + 2))
        self._tri_mat.append(mat)

    # --- primitives (span y0..y1 along the length; centered on X/Z by default) ---
    def frustum(self, y0, y1, w0, t0, w1, t1, mat, cx=0.0, cz=0.0,
                cx1=None, cz1=None) -> None:
        """A tapered box from (w0×t0) at y0 to (w1×t1) at y1.

        ``cx``/``cz`` set the bottom center. ``cx1``/``cz1`` optionally set the
        top center, allowing curved blades to join segment-to-segment without
        lateral steps. A degenerate top (w1=t1=0) makes a pointed tip.
        """
        cx0, cz0 = cx, cz
        cx1 = cx0 if cx1 is None else cx1
        cz1 = cz0 if cz1 is None else cz1
        ctr = np.array([(cx0 + cx1) / 2.0, (y0 + y1) / 2.0, (cz0 + cz1) / 2.0])
        a = [(cx0 - w0 / 2, y0, cz0 - t0 / 2), (cx0 + w0 / 2, y0, cz0 - t0 / 2),
             (cx0 + w0 / 2, y0, cz0 + t0 / 2), (cx0 - w0 / 2, y0, cz0 + t0 / 2)]
        tip = (w1 <= 1e-6 and t1 <= 1e-6)
        if tip:
            apex = (cx1, y1, cz1)
            self._quad(a[3], a[2], a[1], a[0], mat, ctr)            # bottom cap
            for i in range(4):
                self._tri(a[i], a[(i + 1) % 4], apex, mat, ctr)     # 4 side triangles
            return
        b = [(cx1 - w1 / 2, y1, cz1 - t1 / 2), (cx1 + w1 / 2, y1, cz1 - t1 / 2),
             (cx1 + w1 / 2, y1, cz1 + t1 / 2), (cx1 - w1 / 2, y1, cz1 + t1 / 2)]
        self._quad(a[3], a[2], a[1], a[0], mat, ctr)                # bottom
        self._quad(b[0], b[1], b[2], b[3], mat, ctr)               # top
        for i in range(4):
            j = (i + 1) % 4
            self._quad(a[i], a[j], b[j], b[i], mat, ctr)           # sides

    def box(self, y0, y1, w, t, mat, cx=0.0, cz=0.0) -> None:
        self.frustum(y0, y1, w, t, w, t, mat, cx, cz)

    def prism(self, y0, y1, radius, mat, sides=8, cx=0.0, cz=0.0, rtop=None) -> None:
        """An n-gon prism/cone along Y (grips, hafts, pommels). ``rtop`` tapers it."""
        rtop = radius if rtop is None else rtop
        ctr = np.array([cx, (y0 + y1) / 2.0, cz])
        ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        bot = [(cx + radius * np.cos(t_), y0, cz + radius * np.sin(t_)) for t_ in ang]
        top = [(cx + rtop * np.cos(t_), y1, cz + rtop * np.sin(t_)) for t_ in ang]
        for i in range(sides):
            j = (i + 1) % sides
            if rtop <= 1e-6:
                self._tri(bot[i], bot[j], (cx, y1, cz), mat, ctr)
            else:
                self._quad(bot[i], bot[j], top[j], top[i], mat, ctr)
        # end caps (fans)
        for i in range(1, sides - 1):
            self._tri(bot[0], bot[i], bot[i + 1], mat, ctr)
            if rtop > 1e-6:
                self._tri(top[0], top[i + 1], top[i], mat, ctr)

    def build(self):
        """Return (positions f32[N,3], normals f32[N,3], indices u32[M], tri_mat list[str]).
        ``tri_mat`` is the per-triangle material name (the gltf writer groups by it)."""
        if not self._pos:
            raise ValueError("empty mesh")
        pos = np.asarray(self._pos, dtype=_F)
        nrm = np.asarray(self._nrm, dtype=_F)
        idx = np.asarray(self._tris, dtype=np.uint32).reshape(-1)
        return pos, nrm, idx, list(self._tri_mat)

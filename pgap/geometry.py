"""Geometry kernel (DESIGN §3, the heart of M0).

Pipeline: tapered-capsule SDF per bone → polynomial smooth-min blend → sample a
voxel grid sized to the skeleton AABB → hand-rolled numpy marching cubes → weld
duplicate verts → keep the largest connected component → area-weighted normals.

Everything here is pure numpy and deterministic: no RNG draws, no set/dict
ordering, fixed iteration order. The mesh for a given skeleton is identical every
run (the RNG is threaded for interface parity and future jitter, unused in M0).
"""

from __future__ import annotations

import numpy as np

from . import mc_tables
from .rng import Rng
from .spec import Spec
from .types import Bone, Mesh, Primitive

_F = np.float32
_ISO = 0.0
_SMIN_K = 0.07  # smooth-min blend radius; larger = softer fusion between blobs

# A normalized SDF blob: (a, b, radius_a, radius_b) in float64.
_Blob = tuple


# --------------------------------------------------------------------------- #
# SDF primitives
# --------------------------------------------------------------------------- #
def _capsule_sdf(pts: np.ndarray, blob: _Blob) -> np.ndarray:
    """Signed distance from each point to a tapered capsule blob.

    ``pts`` is (K,3). Returns (K,) distance: negative inside the swept volume.
    """
    a, b, ra, rb = blob
    ba = b - a
    pa = pts - a  # (K,3)
    denom = float(np.dot(ba, ba))
    if denom <= 1e-12:
        h = np.zeros(pts.shape[0], dtype=np.float64)
    else:
        h = np.clip((pa @ ba) / denom, 0.0, 1.0)  # (K,)
    closest = a + h[:, None] * ba  # (K,3)
    dist = np.linalg.norm(pts - closest, axis=1)
    radius = ra + h * (rb - ra)
    return dist - radius


def _smin(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """Polynomial smooth-minimum (Inigo Quilez). Fuses two SDFs smoothly."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def _blobs(skel: list[Bone], parts: tuple) -> list[_Blob]:
    """Normalize bones + part primitives into one float64 blob list."""
    out: list[_Blob] = []
    for bone in skel:
        out.append(
            (bone.head.astype(np.float64), bone.tail.astype(np.float64),
             float(bone.radius_head), float(bone.radius_tail))
        )
    for p in parts:
        out.append(
            (np.asarray(p.a, dtype=np.float64), np.asarray(p.b, dtype=np.float64),
             float(p.radius_a), float(p.radius_b))
        )
    return out


def _field(pts: np.ndarray, blobs: list[_Blob]) -> np.ndarray:
    """Blended SDF of all blobs at the given points (K,)."""
    d = _capsule_sdf(pts, blobs[0])
    for blob in blobs[1:]:
        d = _smin(d, _capsule_sdf(pts, blob), _SMIN_K)
    return d


# --------------------------------------------------------------------------- #
# Voxel grid
# --------------------------------------------------------------------------- #
def _grid_bounds(blobs: list[_Blob]) -> tuple[np.ndarray, np.ndarray]:
    pts = []
    max_r = 0.0
    for a, b, ra, rb in blobs:
        pts.append(a)
        pts.append(b)
        max_r = max(max_r, ra, rb)
    pts = np.array(pts, dtype=np.float64)
    margin = max_r + _SMIN_K + 0.05
    lo = pts.min(axis=0) - margin
    hi = pts.max(axis=0) + margin
    return lo, hi


def _resolution(spec: Spec, extent: np.ndarray, res_scale: float = 1.0) -> np.ndarray:
    """Per-axis cell counts. Longest axis gets ``n_max`` cells (from triBudget).

    ``res_scale`` < 1 coarsens the grid — used by the build's budget back-off so
    ``triBudget`` is a true cap even for compact shapes (decimation deferred).
    """
    n_max = int(np.clip(round((spec.tri_budget ** 0.5) * 0.63 * res_scale), 16, 128))
    cell = float(extent.max()) / n_max
    counts = np.maximum(4, np.ceil(extent / cell).astype(int) + 1)
    return counts


def _sample_field(blobs: list[_Blob], spec: Spec, res_scale: float = 1.0):
    lo, hi = _grid_bounds(blobs)
    extent = hi - lo
    counts = _resolution(spec, extent, res_scale)  # (nx,ny,nz) sample counts
    nx, ny, nz = (int(counts[0]), int(counts[1]), int(counts[2]))
    xs = np.linspace(lo[0], hi[0], nx)
    ys = np.linspace(lo[1], hi[1], ny)
    zs = np.linspace(lo[2], hi[2], nz)
    spacing = np.array(
        [xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0]], dtype=np.float64
    )
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    pts = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    field = _field(pts, blobs).reshape(nx, ny, nz)
    return field, lo, spacing


# --------------------------------------------------------------------------- #
# Marching cubes (vectorized over cubes, constant loops over the 256-tables)
# --------------------------------------------------------------------------- #
_EDGE_TABLE = np.array(mc_tables.EDGE_TABLE, dtype=np.int32)
_TRI_TABLE = np.array(mc_tables.TRI_TABLE, dtype=np.int32)
_CORNER_OFFSETS = np.array(mc_tables.CORNER_OFFSETS, dtype=np.float64)
_EDGE_VERTS = np.array(mc_tables.EDGE_VERTS, dtype=np.int32)


def _marching_cubes(field: np.ndarray, origin: np.ndarray, spacing: np.ndarray):
    """Extract an isosurface triangle soup at iso=0 from a scalar field."""
    nx, ny, nz = field.shape

    # Eight corner values per cube; shapes (nx-1, ny-1, nz-1).
    c = [
        field[:-1, :-1, :-1], field[1:, :-1, :-1],
        field[1:, 1:, :-1], field[:-1, 1:, :-1],
        field[:-1, :-1, 1:], field[1:, :-1, 1:],
        field[1:, 1:, 1:], field[:-1, 1:, 1:],
    ]
    cube_index = np.zeros(c[0].shape, dtype=np.int32)
    for i in range(8):
        cube_index |= (c[i] < _ISO).astype(np.int32) << i

    active = (cube_index != 0) & (cube_index != 255)
    if not active.any():
        empty_v = np.zeros((0, 3), dtype=np.float64)
        return empty_v, np.zeros((0, 3), dtype=np.int64)

    sel = np.nonzero(active)  # tuple of (i,),(j,),(k,) arrays, C-order
    base = np.stack(sel, axis=1).astype(np.float64)  # (ncube,3) cube min-corner
    ci = cube_index[sel]  # (ncube,)
    cvals = np.stack([cc[sel] for cc in c], axis=1)  # (ncube,8)
    ncube = base.shape[0]

    # Interpolated vertex position on each of the 12 edges, for every cube.
    edge_pos = np.empty((12, ncube, 3), dtype=np.float64)
    for e in range(12):
        a_corner, b_corner = int(_EDGE_VERTS[e, 0]), int(_EDGE_VERTS[e, 1])
        va = cvals[:, a_corner]
        vb = cvals[:, b_corner]
        pa = origin + (base + _CORNER_OFFSETS[a_corner]) * spacing
        pb = origin + (base + _CORNER_OFFSETS[b_corner]) * spacing
        denom = vb - va
        safe = np.abs(denom) < 1e-12
        denom_safe = np.where(safe, 1.0, denom)
        t = np.where(safe, 0.5, (_ISO - va) / denom_safe)
        edge_pos[e] = pa + t[:, None] * (pb - pa)

    tri = _TRI_TABLE[ci]  # (ncube,16) edge indices, -1 terminated
    cube_ids = np.arange(ncube)
    out_tris = []
    for t in range(5):  # up to 5 triangles per cube
        ea = tri[:, 3 * t]
        eb = tri[:, 3 * t + 1]
        ec = tri[:, 3 * t + 2]
        valid = ea != -1
        if not valid.any():
            continue
        ids = cube_ids[valid]
        va = edge_pos[ea[valid], ids]
        vb = edge_pos[eb[valid], ids]
        vc = edge_pos[ec[valid], ids]
        out_tris.append(np.stack([va, vb, vc], axis=1))  # (k,3,3)

    if not out_tris:
        empty_v = np.zeros((0, 3), dtype=np.float64)
        return empty_v, np.zeros((0, 3), dtype=np.int64)

    soup = np.concatenate(out_tris, axis=0)  # (T,3,3)
    verts = soup.reshape(-1, 3)  # (3T,3), one vert per triangle corner
    faces = np.arange(verts.shape[0]).reshape(-1, 3)
    return verts, faces


# --------------------------------------------------------------------------- #
# Mesh cleanup
# --------------------------------------------------------------------------- #
def _weld(verts: np.ndarray, faces: np.ndarray, tol: float = 1e-5):
    """Merge coincident vertices (quantize → unique). Deterministic ordering."""
    quant = np.round(verts / tol).astype(np.int64)
    _, inv, idx = _unique_rows(quant)
    new_verts = verts[idx]
    new_faces = inv[faces]
    # Drop degenerate triangles (a welded edge collapsed two corners together).
    good = (
        (new_faces[:, 0] != new_faces[:, 1])
        & (new_faces[:, 1] != new_faces[:, 2])
        & (new_faces[:, 0] != new_faces[:, 2])
    )
    return new_verts, new_faces[good]


def _unique_rows(arr: np.ndarray):
    """np.unique over rows returning (unique, inverse, first-index) sorted."""
    uniq, idx, inv = np.unique(
        arr, axis=0, return_index=True, return_inverse=True
    )
    return uniq, inv.reshape(-1), idx


def _largest_component(verts: np.ndarray, faces: np.ndarray):
    """Keep only the largest vertex-connected component (union-find on edges)."""
    n = verts.shape[0]
    if n == 0 or faces.shape[0] == 0:
        return verts, faces
    parent = np.arange(n)

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for f in faces:
        a, b, cc = int(f[0]), int(f[1]), int(f[2])
        ra, rb, rc = find(a), find(b), find(cc)
        if ra != rb:
            parent[rb] = ra
        if ra != rc:
            parent[rc] = ra

    roots = np.array([find(i) for i in range(n)])
    labels, counts = np.unique(roots, return_counts=True)
    keep_root = labels[int(np.argmax(counts))]
    keep_mask = roots == keep_root

    remap = -np.ones(n, dtype=np.int64)
    kept_idx = np.nonzero(keep_mask)[0]
    remap[kept_idx] = np.arange(kept_idx.shape[0])
    face_keep = keep_mask[faces[:, 0]]  # all 3 share a component by construction
    new_faces = remap[faces[face_keep]]
    return verts[kept_idx], new_faces


def _vertex_normals(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals (deterministic scatter-add)."""
    normals = np.zeros_like(verts)
    p0 = verts[faces[:, 0]]
    p1 = verts[faces[:, 1]]
    p2 = verts[faces[:, 2]]
    fn = np.cross(p1 - p0, p2 - p0)  # length ∝ 2*area, weights larger faces
    for k in range(3):
        np.add.at(normals, faces[:, k], fn)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths < 1e-12] = 1.0
    return (normals / lengths).astype(_F)


# --------------------------------------------------------------------------- #
# Public stage entry point
# --------------------------------------------------------------------------- #
def build_geometry(
    skel: list[Bone], spec: Spec, rng: Rng, parts: tuple = ()
) -> Mesh:
    """Skeleton (+ part primitives) → smooth triangle mesh.

    ``parts`` are extra :class:`Primitive` blobs from the part library (M2);
    they are blended into the same SDF as the bone capsules.
    """
    blobs = _blobs(skel, tuple(parts))
    # Budget back-off: re-mesh at coarser resolution until within triBudget.
    # Deterministic (no RNG); typically 1 pass, at most a few.
    res_scale = 1.0
    verts = faces = None
    for _ in range(4):
        field, origin, spacing = _sample_field(blobs, spec, res_scale)
        verts, faces = _marching_cubes(field, origin, spacing)
        verts, faces = _weld(verts, faces)
        verts, faces = _largest_component(verts, faces)
        tris = faces.shape[0]
        if tris <= spec.tri_budget or tris == 0:
            break
        res_scale *= (spec.tri_budget / tris) ** 0.5 * 0.95

    normals = _vertex_normals(verts, faces)
    return Mesh(
        positions=verts.astype(_F),
        normals=normals,
        indices=faces.reshape(-1).astype(np.uint32),
    )


def mesh_stats(mesh: Mesh) -> dict:
    """Lightweight validity stats for the FR4 gate / CLI reporting."""
    faces = mesh.indices.reshape(-1, 3).astype(np.int64)
    # Count how many triangles share each undirected edge.
    e = np.concatenate(
        [faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]], axis=0
    )
    e = np.sort(e, axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return {
        "vertices": mesh.num_vertices,
        "triangles": mesh.num_triangles,
        "boundary_edges": int((counts == 1).sum()),
        "nonmanifold_edges": int((counts > 2).sum()),
        "finite": bool(np.isfinite(mesh.positions).all()),
    }

"""Procedural texture synth (DESIGN §3 texture, M4 + surface treatments).

Base color is the coat palette modulated by a **surface pattern** (fur streaks,
scale cells, feather shingles, chitin segments, bark ridges, or smooth), and the
same pattern drives a tangent-space **normal map** so light catches the relief —
without changing the geometry (the mesh stays one smooth SDF blob). Texture-side
only, seeded → deterministic, numpy-only (a tiny zlib PNG encoder keeps it
dependency-free).
"""

from __future__ import annotations

import struct
import zlib

import numpy as np

from . import palette
from .rng import Rng
from .spec import Spec

_TEX_SIZE = 256

# curated surfaces, their matte/gloss, and how strongly the normal map bites.
SURFACES = ("smooth", "fur", "scales", "feathers", "chitin", "bark")
_ROUGHNESS = {"smooth": 0.85, "fur": 0.95, "scales": 0.45,
              "feathers": 0.70, "chitin": 0.40, "bark": 0.85}
_NORMAL_STRENGTH = {"smooth": 0.0, "fur": 1.1, "scales": 2.4,
                    "feathers": 1.7, "chitin": 2.3, "bark": 2.6}


def _png_rgb(rgb: np.ndarray) -> bytes:
    """Encode an (H,W,3) uint8 array as a PNG (color type 2, no row filter)."""
    h, w, _ = rgb.shape
    rows = np.hstack(
        [np.zeros((h, 1), dtype=np.uint8), rgb.reshape(h, w * 3)]
    ).tobytes()
    comp = zlib.compress(rows, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


def _upsample(grid: np.ndarray, size: int) -> np.ndarray:
    """Bilinear-upsample a coarse (gy, gx) grid to (size, size)."""
    gy, gx = grid.shape
    ty = np.linspace(0.0, gy - 1, size)
    tx = np.linspace(0.0, gx - 1, size)
    iy0 = np.floor(ty).astype(int); iy1 = np.minimum(iy0 + 1, gy - 1); fy = ty - iy0
    ix0 = np.floor(tx).astype(int); ix1 = np.minimum(ix0 + 1, gx - 1); fx = tx - ix0
    rows = grid[iy0] * (1 - fy)[:, None] + grid[iy1] * fy[:, None]   # (size, gx)
    return rows[:, ix0] * (1 - fx)[None, :] + rows[:, ix1] * fx[None, :]


def _norm01(a: np.ndarray) -> np.ndarray:
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def _surf_noise(rng: Rng, size: int, gx: int, gy: int) -> np.ndarray:
    """Two-octave (optionally anisotropic) value noise in ~[0,1]."""
    n = 0.6 * _upsample(rng.random((gy, gx)), size) \
        + 0.4 * _upsample(rng.random((gy * 4, gx * 4)), size)
    return _norm01(n)


def _value_noise(rng: Rng, size: int) -> np.ndarray:
    """Two-octave isotropic value noise (back-compat helper)."""
    return _surf_noise(rng, size, 8, 8)


# --------------------------------------------------------------------------- #
# Surface patterns: each returns (height[0..1], albedo_mult[~0.7..1.2]).
# --------------------------------------------------------------------------- #
def _cells(size: int, n: int) -> np.ndarray:
    """Tileable hex-ish domed cells (scales)."""
    u = np.linspace(0.0, n, size, endpoint=False)
    v = np.linspace(0.0, n, size, endpoint=False)
    uu, vv = np.meshgrid(u, v)
    offset = 0.5 * (np.floor(vv) % 2 == 1)
    fu = (uu + offset)
    fu = fu - np.floor(fu) - 0.5
    fv = vv - np.floor(vv) - 0.5
    d = np.sqrt(fu * fu + fv * fv)
    return np.clip(1.0 - 1.8 * d, 0.0, 1.0)


def _pattern(surface: str, rng: Rng, size: int) -> tuple[np.ndarray, np.ndarray]:
    if surface == "fur":
        s = _surf_noise(rng, size, gx=110, gy=16)   # fine across, long fibers
        return s, 0.78 + 0.42 * s
    if surface == "scales":
        h = _cells(size, 11)
        tone = _surf_noise(rng, size, 11, 11)
        return h, 0.80 + 0.28 * h + 0.08 * (tone - 0.5)
    if surface == "feathers":
        cols = 8
        rows = 16
        uu, vv = np.meshgrid(np.linspace(0, cols, size, endpoint=False),
                             np.linspace(0, rows, size, endpoint=False))
        off = 0.5 * (np.floor(vv) % 2 == 1)
        fu = (uu + off); fu = fu - np.floor(fu) - 0.5
        fv = vv - np.floor(vv)                       # 0 at the top of each feather
        arch = np.clip(1.0 - (2.0 * fu) ** 2, 0.0, 1.0)
        h = arch * (0.55 + 0.45 * (1.0 - fv))
        return h, 0.82 + 0.26 * h
    if surface == "chitin":
        vv = np.linspace(0.0, 9.0, size, endpoint=False)
        band = np.sin(np.clip(vv - np.floor(vv), 0, 1) * np.pi)
        h = np.tile(band[:, None], (1, size))
        return h, 0.80 + 0.30 * h
    if surface == "bark":
        n = _surf_noise(rng, size, gx=40, gy=7)
        h = 1.0 - np.abs(2.0 * n - 1.0)              # vertical ridges
        return h, 0.70 + 0.42 * h
    # smooth (default): flat relief, gentle brightness variation
    s = _value_noise(rng, size)
    return np.full((size, size), 0.5), 0.85 + 0.30 * s


def _height_to_normal(height: np.ndarray, strength: float) -> np.ndarray:
    """Tangent-space normal map (RGB uint8) from a height field. Tileable."""
    h = height.astype(np.float64)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx * inv, ny * inv, nz * inv], axis=-1)
    return (np.clip(n * 0.5 + 0.5, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def synth_textures(spec: Spec, rng: Rng) -> dict:
    """Return the texture bundle: base-color PNG + normal-map PNG + PBR factors.

    Contract (consumed by the assembler): ``{"baseColor": png, "normal": png,
    "roughnessFactor": float, "metallicFactor": float, "surface": str}``.
    """
    mat = spec.material
    surface = str(mat.get("surface", "fur" if mat.get("fur", True) else "smooth")).lower()
    if surface not in SURFACES:
        surface = "smooth"

    base = palette.base_coat(mat)  # sRGB 0..1
    height, mult = _pattern(surface, rng, _TEX_SIZE)
    rgb = np.clip(base[None, None, :] * mult[:, :, None], 0.0, 1.0)
    base_png = _png_rgb((rgb * 255.0 + 0.5).astype(np.uint8))
    normal_png = _png_rgb(_height_to_normal(height, _NORMAL_STRENGTH[surface]))

    return {
        "baseColor": base_png,
        "normal": normal_png,
        "roughnessFactor": float(mat.get("roughness", _ROUGHNESS[surface])),
        "metallicFactor": 0.0,
        "surface": surface,
    }

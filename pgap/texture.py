"""Procedural texture synth (DESIGN §3 texture, M4).

Base color is golden-fur: the coat palette modulated by multi-octave value noise
(seeded RNG → deterministic). This is the procedural fallback; the optional
image-gen base-color path (cached, network) slots in here later behind the same
return contract. Roughness/metallic ship as material factors (fur = matte).

Includes a minimal, dependency-free PNG encoder (zlib, RGB8) so output stays
numpy-only and byte-deterministic.
"""

from __future__ import annotations

import struct
import zlib

import numpy as np

from . import palette
from .rng import Rng
from .spec import Spec

_TEX_SIZE = 256


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


def _bilinear(grid: np.ndarray, size: int) -> np.ndarray:
    """Upsample a coarse (n,n) grid to (size,size) with separable bilinear."""
    n = grid.shape[0]
    t = np.linspace(0.0, n - 1, size)
    i0 = np.floor(t).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    f = t - i0
    rows = grid[i0] * (1 - f)[:, None] + grid[i1] * f[:, None]   # (size, n)
    return rows[:, i0] * (1 - f)[None, :] + rows[:, i1] * f[None, :]


def _value_noise(rng: Rng, size: int) -> np.ndarray:
    """Two-octave value noise in ~[0,1], deterministic from the threaded RNG."""
    coarse = _bilinear(rng.random((8, 8)), size)
    fine = _bilinear(rng.random((32, 32)), size)
    n = 0.6 * coarse + 0.4 * fine
    return (n - n.min()) / (n.max() - n.min() + 1e-9)


def synth_textures(spec: Spec, rng: Rng) -> dict:
    """Return the texture bundle: base-color PNG bytes + PBR factors.

    Contract (consumed by the assembler): ``{"baseColor": png_bytes,
    "roughnessFactor": float, "metallicFactor": float}``.
    """
    base = palette.base_coat(spec.material)  # sRGB 0..1
    noise = _value_noise(rng, _TEX_SIZE)  # (S,S)
    # Fur = base coat * brightness variation; furry coats get stronger streaks.
    strength = 0.30 if spec.material.get("fur", True) else 0.12
    mult = (1.0 - strength) + strength * 2.0 * noise[:, :, None]  # ~[1-s, 1+s]
    rgb = np.clip(base[None, None, :] * mult, 0.0, 1.0)
    png = _png_rgb((rgb * 255.0 + 0.5).astype(np.uint8))
    return {
        "baseColor": png,
        "roughnessFactor": float(spec.material.get("roughness", 0.9)),
        "metallicFactor": 0.0,
    }

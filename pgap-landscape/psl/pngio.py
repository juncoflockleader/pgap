"""Minimal direct PNG writers (stdlib only) — no Pillow dependency.

Dependency-light is a pgap invariant; we encode PNG by hand with zlib + struct,
matching how pgap-3d-actor writes textures directly.
"""

from __future__ import annotations

import struct
import zlib

import numpy as np


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _png(width: int, height: int, bit_depth: int, color_type: int, raw: bytes) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def write_gray16(path: str, arr: np.ndarray) -> None:
    """Write a 2-D uint16 array as a 16-bit grayscale PNG (big-endian samples)."""
    a = np.ascontiguousarray(np.asarray(arr)).astype(">u2")
    if a.ndim != 2:
        raise ValueError("write_gray16 expects a 2-D array")
    h, w = a.shape
    rowbytes = w * 2
    flat = a.tobytes()
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0 (None)
        raw += flat[y * rowbytes : (y + 1) * rowbytes]
    with open(path, "wb") as f:
        f.write(_png(w, h, 16, 0, bytes(raw)))


def write_gray8(path: str, arr: np.ndarray) -> None:
    """Write a 2-D uint8 array as an 8-bit grayscale PNG (for weightmaps, L1+)."""
    a = np.ascontiguousarray(np.asarray(arr)).astype("u1")
    if a.ndim != 2:
        raise ValueError("write_gray8 expects a 2-D array")
    h, w = a.shape
    raw = bytearray()
    flat = a.tobytes()
    for y in range(h):
        raw.append(0)
        raw += flat[y * w : (y + 1) * w]
    with open(path, "wb") as f:
        f.write(_png(w, h, 8, 0, bytes(raw)))


def write_rgb8(path: str, arr: np.ndarray) -> None:
    """Write an (H,W,3) uint8 array as an 8-bit RGB PNG (layer textures, L5)."""
    a = np.ascontiguousarray(np.asarray(arr)).astype("u1")
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("write_rgb8 expects an (H,W,3) array")
    h, w, _ = a.shape
    rowbytes = w * 3
    flat = a.reshape(h, rowbytes).tobytes()
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0 (None)
        raw += flat[y * rowbytes : (y + 1) * rowbytes]
    with open(path, "wb") as f:
        f.write(_png(w, h, 8, 2, bytes(raw)))  # color type 2 = RGB

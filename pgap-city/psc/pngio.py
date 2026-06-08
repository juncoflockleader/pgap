"""Minimal direct PNG writer (stdlib only) — dependency-light, matches the siblings."""

from __future__ import annotations

import struct
import zlib

import numpy as np


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_rgb8(path: str, arr: np.ndarray) -> None:
    """Write an (H,W,3) uint8 array as an 8-bit RGB PNG."""
    a = np.ascontiguousarray(np.asarray(arr)).astype("u1")
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("write_rgb8 expects an (H,W,3) array")
    h, w, _ = a.shape
    rowbytes = w * 3
    flat = a.reshape(h, rowbytes).tobytes()
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        raw += flat[y * rowbytes:(y + 1) * rowbytes]
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    with open(path, "wb") as f:
        f.write(sig + _chunk(b"IHDR", ihdr)
                + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b""))

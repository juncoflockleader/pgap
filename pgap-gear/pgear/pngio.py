"""Minimal direct PNG writer (stdlib only) — matches the sibling pipelines."""

from __future__ import annotations

import struct
import zlib

import numpy as np


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_rgb8(arr: np.ndarray) -> bytes:
    a = np.ascontiguousarray(np.asarray(arr)).astype("u1")
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("encode_rgb8 expects an (H,W,3) array")
    h, w, _ = a.shape
    flat = a.reshape(h, w * 3).tobytes()
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += flat[y * w * 3:(y + 1) * w * 3]
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")


def write_rgb8(path: str, arr: np.ndarray) -> None:
    with open(path, "wb") as f:
        f.write(encode_rgb8(arr))

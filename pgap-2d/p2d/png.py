"""Minimal RGBA PNG writer — stdlib only (zlib + struct), no PIL.

Deterministic output: fixed zlib level, no timestamps, no ancillary chunks.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np


def to_bytes(img: np.ndarray) -> bytes:
    """Encode an (H, W, 4) array (float 0..1 or uint8) as PNG bytes."""
    if img.ndim != 3 or img.shape[2] != 4:
        raise ValueError("expected an (H, W, 4) RGBA array")
    if img.dtype != np.uint8:
        img = (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    h, w = img.shape[:2]
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def write_png(path: str | Path, img: np.ndarray) -> None:
    Path(path).write_bytes(to_bytes(img))

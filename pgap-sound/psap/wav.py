"""Hand-written PCM16 WAV writer (and reader for tests). Deterministic bytes."""

from __future__ import annotations

import struct

import numpy as np


def to_pcm16(samples) -> np.ndarray:
    """Clip float samples to [-1, 1] and convert to little-endian int16."""
    s = np.clip(np.asarray(samples, dtype=np.float64), -1.0, 1.0)
    return (s * 32767.0).round().astype("<i2")


def wav_bytes(samples, sample_rate: int = 44100, channels: int = 1) -> bytes:
    """Return a complete canonical 44-byte-header PCM16 WAV as bytes."""
    pcm = to_pcm16(samples)
    data = pcm.tobytes()
    byte_rate = sample_rate * channels * 2
    block_align = channels * 2
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
                                    byte_rate, block_align, 16)
    header += b"data" + struct.pack("<I", len(data))
    return header + data


def write_wav(path, samples, sample_rate: int = 44100, channels: int = 1) -> bytes:
    b = wav_bytes(samples, sample_rate, channels)
    with open(path, "wb") as f:
        f.write(b)
    return b


def read_wav(path):
    """Minimal reader -> (float_samples, sample_rate, channels). For tests."""
    with open(path, "rb") as f:
        b = f.read()
    if b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE file")
    channels, sr = struct.unpack("<HI", b[22:28])
    di = b.find(b"data")
    size = struct.unpack("<I", b[di + 4:di + 8])[0]
    pcm = np.frombuffer(b[di + 8:di + 8 + size], dtype="<i2")
    return pcm.astype(np.float64) / 32767.0, sr, channels

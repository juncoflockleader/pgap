"""S0: the WAV writer emits a valid canonical PCM16 file."""

import struct

import numpy as np

from psap import render_spec, wav

from .helpers import load_fixture


def test_header_is_canonical_pcm16():
    spec = load_fixture("laser")
    buf = render_spec(spec)
    b = wav.wav_bytes(buf, spec.sample_rate)

    assert b[:4] == b"RIFF" and b[8:12] == b"WAVE"
    assert b[12:16] == b"fmt "
    size, audio_fmt, channels, sr, byte_rate, block_align, bits = struct.unpack(
        "<IHHIIHH", b[16:36])
    assert size == 16 and audio_fmt == 1 and channels == 1
    assert sr == spec.sample_rate and bits == 16
    assert byte_rate == sr * channels * 2 and block_align == channels * 2
    assert b[36:40] == b"data"

    data_size = struct.unpack("<I", b[40:44])[0]
    assert data_size == buf.size * 2
    assert struct.unpack("<I", b[4:8])[0] == 36 + data_size


def test_roundtrip_and_no_nan_or_inf(tmp_path):
    spec = load_fixture("bark")
    buf = render_spec(spec)
    assert np.all(np.isfinite(buf))
    p = tmp_path / "bark.wav"
    wav.write_wav(p, buf, spec.sample_rate)
    back, sr, ch = wav.read_wav(p)
    assert sr == spec.sample_rate and ch == 1
    assert back.size == buf.size
    assert np.all(np.abs(back) <= 1.0)

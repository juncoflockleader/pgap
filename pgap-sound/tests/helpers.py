"""Shared test helpers."""

from __future__ import annotations

import json
from pathlib import Path

from psap import render_spec, wav
from psap.spec import SoundSpec

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> SoundSpec:
    return SoundSpec.from_dict(json.loads((FIXTURES / f"{name}.json").read_text()))


def render_bytes(spec: SoundSpec) -> bytes:
    buf = render_spec(spec)
    return wav.wav_bytes(buf, spec.sample_rate)

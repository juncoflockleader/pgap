"""SoundSpec — the structured input an LLM or human authors, and its hash."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields


@dataclass
class SoundSpec:
    name: str = "Sound"
    category: str = "sfx"          # sfx | ui | vocal
    seed: int = 0
    duration_ms: float = 400.0
    sample_rate: int = 44100
    gain_dbfs: float = -1.0        # target peak loudness (<= 0)
    graph: dict = field(default_factory=dict)  # category-specific synth params

    @classmethod
    def from_dict(cls, d: dict) -> "SoundSpec":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> dict:
        return asdict(self)

    def spec_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

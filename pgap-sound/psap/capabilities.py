"""The machine-readable contract (what an LLM authors against) + fail-closed
validation. Unsupported requests return errors — the generator never guesses.
"""

from __future__ import annotations

from .ambient import AMBIENT_PRESETS
from .dsp import WAVES
from .impact import MATERIAL_PRESETS
from .sfx import SFX_PRESETS
from .vocal import VOCAL_PRESETS

SCHEMA_VERSION = "psap.capabilities.v1"
CATEGORIES = ("sfx", "ui", "vocal", "impact", "ambient")
FX = ("bitcrush",)
SAMPLE_RATES = (22050, 44100, 48000)
MAX_DURATION_MS = 10000.0


def capability_report() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generator": "psap",
        "categories": list(CATEGORIES),
        "waves": list(WAVES),
        "fx": list(FX),
        "sampleRates": list(SAMPLE_RATES),
        "maxDurationMs": MAX_DURATION_MS,
        "sfxPresets": sorted(SFX_PRESETS),
        "vocalPresets": sorted(VOCAL_PRESETS),
        "impactMaterials": sorted(MATERIAL_PRESETS),
        "ambientPresets": sorted(AMBIENT_PRESETS),
        "limits": {
            "gainDbfs": {"min": -60.0, "max": 0.0},
            "durationMs": {"min": 1.0, "max": MAX_DURATION_MS},
            "variance": {"min": 0.0, "max": 1.0},
        },
        "variance": "0 = exact preset; >0 = seeded humanization — change the seed "
                    "for a different take of the same sound (deterministic per seed).",
        "notes": "Synthesized, not recorded. Not music, not voice — mainly sound.",
    }


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_spec(d: dict) -> tuple[bool, list[str]]:
    """Return (ok, errors). Fail-closed: any unsupported field is an error."""
    errors: list[str] = []

    cat = d.get("category")
    if cat not in CATEGORIES:
        errors.append(f"category {cat!r} not in {list(CATEGORIES)}")

    name = d.get("name", "Sound")
    if not isinstance(name, str) or not name:
        errors.append("name must be a non-empty string")

    dur = d.get("duration_ms", 400.0)
    if not _num(dur) or not (0.0 < dur <= MAX_DURATION_MS):
        errors.append(f"duration_ms must be in (0, {MAX_DURATION_MS}]")

    sr = d.get("sample_rate", 44100)
    if sr not in SAMPLE_RATES:
        errors.append(f"sample_rate {sr!r} not in {list(SAMPLE_RATES)}")

    gain = d.get("gain_dbfs", -1.0)
    if not _num(gain) or not (-60.0 <= gain <= 0.0):
        errors.append("gain_dbfs must be in [-60, 0]")

    var = d.get("variance", 0.0)
    if not _num(var) or not (0.0 <= var <= 1.0):
        errors.append("variance must be in [0, 1]")

    g = d.get("graph", {})
    if not isinstance(g, dict):
        errors.append("graph must be an object")
        return (False, errors)

    wave = g.get("wave")
    if wave is not None and wave not in WAVES:
        errors.append(f"graph.wave {wave!r} not in {list(WAVES)}")

    for k in ("freq", "f0", "f1", "fpeak", "sweep", "base_freq", "lowpass", "highpass"):
        if k in g and g[k] is not None and not _num(g[k]):
            errors.append(f"graph.{k} must be numeric")
    for k in ("freq", "f0", "f1", "fpeak", "base_freq", "lowpass", "highpass"):
        if k in g and _num(g[k]) and g[k] <= 0:
            errors.append(f"graph.{k} must be > 0")

    if cat == "impact":
        mat = g.get("material")
        if mat is not None and mat not in MATERIAL_PRESETS:
            errors.append(f"graph.material {mat!r} not in {sorted(MATERIAL_PRESETS)}")

    tone = g.get("tone")
    if tone is not None and not (isinstance(tone, list) and all(_num(x) and x > 0 for x in tone)):
        errors.append("graph.tone must be a list of positive frequencies")

    arp = g.get("arpeggio")
    if arp is not None and not (isinstance(arp, list) and all(_num(x) for x in arp)):
        errors.append("graph.arpeggio must be a list of numbers (semitone offsets)")

    fx = g.get("fx", [])
    if not isinstance(fx, list) or any(x not in FX for x in fx):
        errors.append(f"graph.fx must be a subset of {list(FX)}")

    noise = g.get("noise")
    if noise is not None and (not _num(noise) or not (0.0 <= noise <= 1.0)):
        errors.append("graph.noise must be in [0, 1]")

    return (len(errors) == 0, errors)

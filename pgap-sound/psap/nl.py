"""Deterministic natural-language front-end: a prompt -> a SoundSpec.

Keyword inference only (no model). Fails closed: an unrecognized prompt raises,
it does not guess. The earliest-matching keyword in the prompt wins (ties broken
by the longer, more specific keyword).
"""

from __future__ import annotations

import copy

from .ambient import AMBIENT_PRESETS
from .impact import IMPACT_PRESETS
from .sfx import SFX_PRESETS
from .spec import SoundSpec
from .vocal import VOCAL_PRESETS

# (keyword, preset) — preset names resolve in SFX_PRESETS or VOCAL_PRESETS.
KEYWORDS: list[tuple[str, str]] = [
    ("laser", "laser"), ("zap", "laser"), ("pew", "laser"), ("blaster", "laser"),
    ("coin", "coin"), ("gold", "coin"),
    ("pickup", "pickup"), ("collect", "pickup"), ("gem", "pickup"), ("orb", "pickup"),
    ("powerup", "powerup"), ("power-up", "powerup"), ("upgrade", "powerup"),
    ("levelup", "powerup"), ("level-up", "powerup"),
    ("jump", "jump"), ("hop", "jump"), ("leap", "jump"), ("bounce", "jump"),
    ("explosion", "explosion"), ("explode", "explosion"), ("boom", "explosion"),
    ("blast", "explosion"),
    ("hit", "hit"), ("hurt", "hit"), ("punch", "hit"), ("damage", "hit"),
    ("blip", "blip"), ("select", "blip"), ("menu", "blip"), ("click", "blip"),
    ("beep", "blip"), ("button", "blip"),
    ("bark", "bark"), ("woof", "bark"), ("dog", "bark"),
    ("growl", "growl"), ("snarl", "growl"),
    ("roar", "roar"), ("dragon", "roar"), ("monster", "roar"), ("beast", "roar"),
    ("chirp", "chirp"), ("bird", "chirp"), ("tweet", "chirp"),
    ("squeak", "squeak"), ("mouse", "squeak"), ("rat", "squeak"),
    # impacts (modal synthesis) — material collision sounds
    ("wood", "wood"), ("wooden", "wood"), ("knock", "wood"),
    ("metal", "metal"), ("metallic", "metal"), ("clang", "metal"), ("clank", "metal"),
    ("glass", "glass"), ("smash", "glass"), ("shatter", "glass"),
    ("stone", "stone"), ("rock", "stone"), ("thud", "stone"),
    # ambient loops
    ("wind", "wind"), ("breeze", "wind"), ("gale", "wind"),
    ("rain", "rain"), ("drizzle", "rain"),
    ("fire", "fire"), ("campfire", "fire"), ("flame", "fire"), ("crackle", "fire"),
    ("water", "water"), ("stream", "water"), ("river", "water"), ("bubbl", "water"),
    ("hum", "hum"),
    ("drone", "drone"), ("ambience", "drone"), ("ambient", "drone"), ("rumble", "drone"),
]

_BIGGER = ("big", "large", "deep", "low", "heavy", "huge", "giant")
_SMALLER = ("small", "tiny", "little", "high", "baby")
_RETRO = ("retro", "8-bit", "8bit", "chiptune", "arcade", "nes")


def _preset_def(preset: str):
    if preset in SFX_PRESETS:
        return SFX_PRESETS[preset]
    if preset in VOCAL_PRESETS:
        return VOCAL_PRESETS[preset]
    if preset in IMPACT_PRESETS:
        return IMPACT_PRESETS[preset]
    if preset in AMBIENT_PRESETS:
        return AMBIENT_PRESETS[preset]
    raise KeyError(preset)


def spec_from_preset(preset: str, seed: int = 0, name: str | None = None) -> SoundSpec:
    d = _preset_def(preset)
    return SoundSpec(
        name=name or preset.capitalize(),
        category=d["category"],
        seed=seed,
        duration_ms=d["duration_ms"],
        graph=copy.deepcopy(d["graph"]),
    )


def prompt_to_spec(prompt: str, seed: int = 0, name: str | None = None,
                   variance: float = 0.2) -> SoundSpec:
    p = prompt.lower()

    best = None  # (position, keyword, preset)
    for kw, preset in KEYWORDS:
        i = p.find(kw)
        if i >= 0 and (best is None or i < best[0] or (i == best[0] and len(kw) > len(best[1]))):
            best = (i, kw, preset)
    if best is None:
        raise ValueError(
            f"could not infer a sound from {prompt!r}; supported: lasers, coins, "
            "pickups, powerups, jumps, hits, explosions, UI blips, and vocals "
            "(bark/growl/roar/chirp/squeak)"
        )

    preset = best[2]
    spec = spec_from_preset(preset, seed=seed, name=name)
    spec.variance = variance
    g = spec.graph

    fscale, dscale = 1.0, 1.0
    if any(w in p for w in _BIGGER):
        fscale *= 0.6
        dscale *= 1.3
    if any(w in p for w in _SMALLER):
        fscale *= 1.5
        dscale *= 0.8
    if "long" in p:
        dscale *= 1.6
    if any(w in p for w in ("short", "quick", "fast")):
        dscale *= 0.7

    if abs(fscale - 1.0) > 1e-9:
        for k in ("freq", "f0", "fpeak", "f1", "base_freq"):
            if k in g and isinstance(g[k], (int, float)):
                g[k] = round(g[k] * fscale, 2)
    if abs(dscale - 1.0) > 1e-9:
        spec.duration_ms = round(spec.duration_ms * dscale, 1)

    if any(w in p for w in _RETRO):
        fx = list(g.get("fx", []))
        if "bitcrush" not in fx:
            fx.append("bitcrush")
        g["fx"] = fx

    _apply_adjectives(p, spec)

    if name is None:
        spec.name = "".join(w.capitalize() for w in preset.split("_"))
    return spec


def _scale_cutoffs(g: dict, factor: float) -> None:
    """Brighten/darken: scale any cutoff-like field in the graph."""
    filt = g.get("filter")
    if isinstance(filt, dict) and isinstance(filt.get("cutoff"), (int, float)):
        filt["cutoff"] = round(filt["cutoff"] * factor, 1)
    for k in ("lowpass", "noise_cut", "transient_cut"):
        if isinstance(g.get(k), (int, float)):
            g[k] = round(g[k] * factor, 1)


def _apply_adjectives(p: str, spec: SoundSpec) -> None:
    """Variant adjectives: tweak timbre params and/or append effects."""
    g = spec.graph
    is_loop = spec.category == "ambient"

    if any(w in p for w in ("bright", "sharp", "crisp", "shrill")):
        _scale_cutoffs(g, 1.7)
    if any(w in p for w in ("dark", "muffled", "dull", "soft", "mellow")):
        _scale_cutoffs(g, 0.55)
    if "metallic" in p or ("metal" in p and spec.category == "vocal"):
        if isinstance(g.get("mod_index"), (int, float)):
            g["mod_index"] = round(g["mod_index"] * 1.7, 2)
        spec.effects.append({"type": "reverb", "decay": 0.5, "wet": 0.28})

    added_tail = False
    if any(w in p for w in ("reverberant", "cavernous", "spacious", "hall",
                            "in a cave", "echoey hall")):
        spec.effects.append({"type": "reverb", "decay": 0.8, "wet": 0.4})
        added_tail = True
    if any(w in p for w in ("echo", "echoey", "delay", "delayed")):
        spec.effects.append({"type": "delay", "time_ms": 160, "feedback": 0.42, "wet": 0.4})
        added_tail = True
    if any(w in p for w in ("distorted", "gritty", "harsh", "crunchy", "dirty", "growly")):
        spec.effects.append({"type": "distortion", "drive": 5.0, "wet": 0.85})
    if any(w in p for w in ("lush", "chorus", "wobbly", "shimmer", "wide")):
        spec.effects.append({"type": "chorus", "rate_hz": 1.4, "depth_ms": 3.0, "wet": 0.45})
    if "warm" in p:
        spec.effects.append({"type": "distortion", "drive": 2.0, "wet": 0.5})

    # Give one-shots room for the reverb/echo tail (loops wrap, so leave them).
    if added_tail and not is_loop:
        spec.duration_ms = round(min(10000.0, spec.duration_ms * 2.5 + 500.0), 1)

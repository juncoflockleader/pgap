"""Analysis-driven synthesis (offline, design-time): measure a real sample and
emit synth parameters, so presets stop *guessing* and start *fitting*.

`analyze_impact` does modal analysis on a recorded impact one-shot: short-time FFT
→ pick the persistent spectral peaks (the resonant modes) → fit each mode's
exponential decay over time → return `{base_freq, partials, transient}` in exactly
the format `impact.synth` consumes. The runtime never sees the sample — only the
measured numbers get baked into a preset. Pure numpy.

CLI:  python -m psap.analyze <wav> [--material NAME] [--modes K]
"""

from __future__ import annotations

import json
import sys

import numpy as np

from . import wav


def _onset(x: np.ndarray, sr: int) -> int:
    """Index a few ms before the loudest sample (the strike)."""
    peak = int(np.argmax(np.abs(x)))
    return max(0, peak - int(0.003 * sr))


def _stft(x: np.ndarray, sr: int, win: int = 2048, hop: int = 256):
    if x.size < win:
        x = np.pad(x, (0, win - x.size))
    w = np.hanning(win)
    nframes = 1 + (x.size - win) // hop
    frames = np.stack([x[i * hop:i * hop + win] * w for i in range(nframes)])
    spec = np.abs(np.fft.rfft(frames, axis=1))  # (nframes, win//2+1)
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    return spec, freqs, hop


def _pick_peaks(spectrum: np.ndarray, freqs: np.ndarray, n: int,
                fmin: float = 70.0, fmax: float = 12000.0,
                min_sep_hz: float = 60.0) -> list[int]:
    """Indices of the n strongest spectral peaks (local maxima, fmin..fmax, spaced)."""
    band = (freqs >= fmin) & (freqs <= fmax)
    cand = []
    for i in range(1, spectrum.size - 1):
        if band[i] and spectrum[i] > spectrum[i - 1] and spectrum[i] >= spectrum[i + 1]:
            cand.append(i)
    cand.sort(key=lambda i: spectrum[i], reverse=True)
    chosen: list[int] = []
    for i in cand:
        if all(abs(freqs[i] - freqs[j]) >= min_sep_hz for j in chosen):
            chosen.append(i)
        if len(chosen) >= n:
            break
    return sorted(chosen, key=lambda i: freqs[i])


def _decay_seconds(mag_t: np.ndarray, hop: int, sr: int) -> float:
    """Fit an exponential to a mode's magnitude envelope -> decay time constant."""
    p0 = int(np.argmax(mag_t))
    seg = mag_t[p0:]
    floor = seg.max() * 0.05
    keep = seg > floor
    if keep.sum() < 3:
        return 0.08
    t = np.arange(seg.size)[keep] * hop / sr
    logm = np.log(seg[keep] + 1e-9)
    slope = np.polyfit(t, logm, 1)[0]
    if slope >= -1e-3:
        return 1.0
    return float(np.clip(-1.0 / slope, 0.01, 3.0))


def analyze_impact(samples: np.ndarray, sr: int, n_modes: int = 6) -> dict:
    """Modal analysis of an impact one-shot -> impact-graph params."""
    x = np.asarray(samples, dtype=np.float64)
    x = x[_onset(x, sr):]
    x = x / (np.max(np.abs(x)) + 1e-9)

    spec, freqs, hop = _stft(x, sr)
    # average over the early ring (where the modes are excited and sustained)
    early = spec[: min(spec.shape[0], int(0.15 * sr / hop) + 1)]
    avg = early.mean(axis=0)

    peaks = _pick_peaks(avg, freqs, n_modes)
    if not peaks:
        peaks = [int(np.argmax(avg))]

    modes = []  # (freq, gain, decay_s)
    for b in peaks:
        decay = _decay_seconds(spec[:, b], hop, sr)
        modes.append((float(freqs[b]), float(avg[b]), decay))

    # drop near-noise modes (keep the audible resonances), always keep the strongest
    gmax = max(g for _, g, _ in modes)
    modes = [m for m in modes if m[1] >= 0.03 * gmax] or [max(modes, key=lambda m: m[1])]
    modes.sort(key=lambda m: m[0])

    base = modes[0][0]
    gmax = max(g for _, g, _ in modes) + 1e-9
    partials = [[round(f / base, 4), round(g / gmax, 4), round(d, 4)] for f, g, d in modes]

    # contact transient: high-frequency energy in the first ~8 ms vs the whole hit
    n8 = int(0.008 * sr)
    hi = np.abs(np.diff(x[:n8])).mean() if n8 > 1 else 0.0
    lo = np.abs(np.diff(x)).mean() + 1e-9
    transient = float(np.clip(0.20 + 0.25 * (hi / lo - 1.0), 0.1, 0.5))

    dur_ms = float(round(min(3.0, x.size / sr) * 1000.0, 1))
    return {
        "base_freq": round(base, 2),
        "partials": partials,
        "transient": round(transient, 3),
        "duration_ms": dur_ms,
        "n_modes": len(partials),
    }


def _main(argv: list[str]) -> int:
    if not argv:
        print("usage: python -m psap.analyze <wav> [--material NAME] [--modes K]",
              file=sys.stderr)
        return 2
    path = argv[0]
    material = "measured"
    modes = 6
    for i, a in enumerate(argv):
        if a == "--material" and i + 1 < len(argv):
            material = argv[i + 1]
        if a == "--modes" and i + 1 < len(argv):
            modes = int(argv[i + 1])

    samples, sr, _ = wav.read_wav(path)
    g = analyze_impact(samples, sr, n_modes=modes)
    preset = {material: {"category": "impact", "duration_ms": g["duration_ms"], "graph": {
        "material": material, "base_freq": g["base_freq"], "transient": g["transient"],
        "partials": g["partials"]}}}
    print(json.dumps(preset, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

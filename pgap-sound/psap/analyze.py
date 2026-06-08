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


def _levinson(r: np.ndarray, order: int) -> np.ndarray:
    """Levinson-Durbin recursion: autocorrelation -> LPC coefficients [1, a1..ap]."""
    a = np.zeros(order + 1)
    a[0] = 1.0
    e = float(r[0])
    if e <= 0:
        return a
    for i in range(1, order + 1):
        acc = r[i] + sum(a[j] * r[i - j] for j in range(1, i))
        k = -acc / e
        anew = a.copy()
        for j in range(1, i):
            anew[j] = a[j] + k * a[i - j]
        anew[i] = k
        a = anew
        e *= (1.0 - k * k)
        if e <= 0:
            break
    return a


def _lpc_formants(x: np.ndarray, sr: int, n_formants: int = 4) -> list[list[float]]:
    """Estimate formants via LPC: roots of the LPC polynomial -> resonant peaks."""
    x = x * np.hanning(x.size)
    order = int(2 + sr / 1000)  # ~ 2 + 1 per kHz
    full = np.correlate(x, x, "full")
    r = full[x.size - 1: x.size - 1 + order + 1]
    a = _levinson(r, order)
    roots = [z for z in np.roots(a) if np.imag(z) > 1e-6]
    out = []
    for z in roots:
        freq = float(np.arctan2(np.imag(z), np.real(z)) * sr / (2.0 * np.pi))
        bw = float(-0.5 * sr / np.pi * np.log(abs(z) + 1e-12))
        if 150.0 < freq < 5000.0 and bw < 700.0:
            out.append([round(freq, 1), round(max(2.0, freq / max(bw, 1.0)), 2), 1.0])
    out.sort(key=lambda f: f[0])
    return out[:n_formants]


def _autocorr_f0(frame: np.ndarray, sr: int, fmin: float = 70.0, fmax: float = 1400.0) -> float:
    ac = np.correlate(frame, frame, "full")[frame.size - 1:]
    if ac[0] <= 0:
        return 0.0
    lo, hi = int(sr / fmax), min(int(sr / fmin), ac.size - 1)
    if hi <= lo:
        return 0.0
    lag = lo + int(np.argmax(ac[lo:hi]))
    return sr / lag if ac[lag] / ac[0] > 0.3 else 0.0


def analyze_vocal(samples: np.ndarray, sr: int) -> dict:
    """Measure a voiced one-shot: pitch contour (f0/fpeak/f1) + formants + noise."""
    x = np.asarray(samples, dtype=np.float64)
    x = x[_onset(x, sr):]
    x = x / (np.max(np.abs(x)) + 1e-9)

    # pitch track over voiced frames
    win, hop = 1024, 256
    f0s = []
    for i in range(0, max(1, x.size - win), hop):
        f = _autocorr_f0(x[i:i + win], sr)
        if f > 0:
            f0s.append(f)
    f0s = f0s or [220.0]
    contour = {"f0": round(f0s[0], 1), "fpeak": round(max(f0s), 1), "f1": round(f0s[-1], 1)}

    # formants from the loudest (most voiced) frame
    p = int(np.argmax(np.abs(x)))
    seg = x[max(0, p - win // 2): p + win // 2]
    formants = _lpc_formants(seg, sr) if seg.size > 32 else []

    # harmonic/noise: zero-crossing rate proxy for breathiness
    zcr = float(np.mean(np.abs(np.diff(np.sign(x))) > 0))
    noise = float(np.clip((zcr - 0.05) * 1.5, 0.0, 0.6))

    return {
        **contour, "formants": formants, "noise": round(noise, 3),
        "duration_ms": round(x.size / sr * 1000.0, 1), "n_formants": len(formants),
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

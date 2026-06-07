"""psap CLI — `python -m psap.cli` (or `python pgap.py sound ...`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import nl
from .capabilities import capability_report, validate_spec
from .pipeline import generate
from .spec import SoundSpec


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="psap", description="Procedural Sound Asset Pipeline — synthesize "
        "game-ready SFX / UI / creature vocals (deterministic, offline).")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--spec", help="path to a SoundSpec JSON file")
    src.add_argument("--describe", "--prompt", dest="describe",
                     help="natural-language description, e.g. 'a retro coin pickup'")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (default 0)")
    p.add_argument("--name", help="override the output asset name")
    p.add_argument("--out", default="out", help="output directory (default ./out)")
    p.add_argument("--capabilities", action="store_true",
                   help="print the machine-readable capability report and exit")
    p.add_argument("--handoff", action="store_true",
                   help="also emit the unreal-mcp-rx audio source-handoff bundle")
    p.add_argument("--package-root", help="UE package root for the handoff manifest")
    return p


def _load_spec(args) -> SoundSpec:
    if args.spec:
        data = json.loads(Path(args.spec).read_text())
        if args.name:
            data["name"] = args.name
        if args.seed:
            data["seed"] = args.seed
        return SoundSpec.from_dict(data)
    return nl.prompt_to_spec(args.describe, seed=args.seed, name=args.name)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.capabilities:
        print(json.dumps(capability_report(), indent=2))
        return 0

    if not args.spec and not args.describe:
        print("error: provide --spec FILE or --describe TEXT (or --capabilities)",
              file=sys.stderr)
        return 2

    try:
        spec = _load_spec(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    ok, errors = validate_spec(spec.to_dict())
    if not ok:
        print("error: spec failed validation (fail-closed):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    manifest, buf = generate(spec, args.out, handoff=args.handoff,
                             package_root=args.package_root)
    peak = float(np.max(np.abs(buf))) if buf.size else 0.0
    peak_db = 20.0 * np.log10(peak) if peak > 0 else float("-inf")

    print(f"sound → {spec.name} ({spec.category})")
    print(f"wrote {Path(args.out) / (spec.name + '.wav')}")
    print(f"  duration   {spec.duration_ms:g} ms · {spec.sample_rate} Hz · {buf.size} samples")
    print(f"  peak       {peak_db:.1f} dBFS")
    if args.handoff:
        print(f"  handoff    {Path(args.out) / 'handoff'}/ (S_{spec.name}.wav)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

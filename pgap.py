#!/usr/bin/env python3
"""pgap — Procedural Generative Asset Pipeline (multi-pipeline wrapper).

One umbrella over several deterministic, offline, dependency-light generators.
This script routes a *mode* to its sub-pipeline; all remaining arguments are
passed through unchanged to that pipeline's own CLI.

Modes:
  3d-actor   rigged / skinned / animated / textured creatures      (implemented)
  sound      SFX / impacts / ambient / stylized creature vocals     (implemented)
  2d         stylized portraits + battle backdrops (PNG)            (implemented)
  landscape  biome terrain: heightmap + layers + scatter            (scaffold)
  city       modular building kits + city layouts                   (scaffold)
  gear       weapons / apparel / armor / accessories                (implemented)

Usage:
  python pgap.py <mode> [args...]
  python pgap.py 3d-actor --creature dragon --color crimson --out out
  python pgap.py 3d-actor --describe "a deer-antlered dragon with feathered wings"
  python pgap.py sound --help
  python pgap.py --help        # list modes

Each sub-pipeline is a self-contained folder with its own package + CLI; the
wrapper runs it as a subprocess with that folder as the working directory, so its
package imports and relative paths resolve there.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# mode -> (subfolder, module run via `python -m`, implemented yet?)
PIPELINES: dict[str, dict] = {
    "3d-actor": {"dir": "pgap-3d-actor", "module": "pgap.cli", "ready": True,
                 "desc": "rigged / skinned / animated / textured creatures"},
    "sound":    {"dir": "pgap-sound", "module": "psap.cli", "ready": True,
                 "desc": "SFX / impacts / ambient / stylized creature vocals"},
    "2d":       {"dir": "pgap-2d", "module": "p2d.cli", "ready": True,
                 "desc": "stylized portraits + battle backdrops (PNG)"},
    "landscape": {"dir": "pgap-landscape", "module": "psl.cli", "ready": True,
                  "desc": "biome terrain: heightmap + layers + scatter"},
    "city":     {"dir": "pgap-city", "module": "psc.cli", "ready": True,
                 "desc": "modular building kits + city layouts"},
    "gear":     {"dir": "pgap-gear", "module": "pgear.cli", "ready": True,
                 "desc": "weapons / apparel / armor / accessories"},
}


def _usage() -> None:
    print(__doc__.strip())
    print("\nmodes:")
    for name, p in PIPELINES.items():
        flag = "" if p["ready"] else "  (planned — see {}/)".format(p["dir"])
        print(f"  {name:9s} {p['desc']}{flag}")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        _usage()
        return 0

    mode, rest = argv[0], argv[1:]
    p = PIPELINES.get(mode)
    if p is None:
        print(f"unknown mode {mode!r}; choose from: {', '.join(PIPELINES)}", file=sys.stderr)
        return 2

    sub = ROOT / p["dir"]
    if not p["ready"]:
        print(f"[{mode}] pipeline is planned, not yet implemented — see {p['dir']}/",
              file=sys.stderr)
        return 3

    # Run the sub-pipeline CLI with cwd = its folder so its package + paths resolve.
    return subprocess.call([sys.executable, "-m", p["module"], *rest], cwd=str(sub))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Write the WAV + provenance manifest, and (optionally) the unreal-mcp-rx
source-handoff bundle for the audio role."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import __version__, wav
from .spec import SoundSpec


def _sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def write_outputs(spec: SoundSpec, buf, out_dir, handoff: bool = False,
                  package_root=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    wav_name = f"{spec.name}.wav"
    data = wav.write_wav(out / wav_name, buf, spec.sample_rate)

    manifest = {
        "schemaVersion": "psap.manifest.v1",
        "generator": "psap",
        "version": __version__,
        "name": spec.name,
        "category": spec.category,
        "seed": spec.seed,
        "durationMs": spec.duration_ms,
        "sampleRate": spec.sample_rate,
        "gainDbfs": spec.gain_dbfs,
        "specHash": spec.spec_hash(),
        "files": [{"path": wav_name, "role": "sound", "sha1": _sha1(data)}],
        "license": "procedurally generated original work",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    if handoff:
        manifest["handoff"] = _export_handoff(spec, data, out, package_root)
    return manifest


def _export_handoff(spec: SoundSpec, data: bytes, out: Path, package_root) -> dict:
    """Emit the audio-role bundle the unreal-mcp-rx source-handoff contract reads:
    an `S_<Name>.wav` role file + an import sidecar describing the SoundWave."""
    bundle = out / "handoff"
    bundle.mkdir(parents=True, exist_ok=True)

    role_name = f"S_{spec.name}.wav"
    (bundle / role_name).write_bytes(data)

    sidecar = {
        "schemaVersion": "psap.sound.import.v1",
        "asset": f"S_{spec.name}",
        "sourceFile": role_name,
        "assetType": "SoundWave",
        "factory": "SoundFactory",
        "sampleRate": spec.sample_rate,
        "channels": 1,
        "looping": spec.category == "ambient",
        "compression": "default",
    }
    (bundle / f"{spec.name}.sound.import.json").write_text(
        json.dumps(sidecar, indent=2, sort_keys=True))

    handoff_manifest = {
        "schemaVersion": "game.interactive_component_agent_source_manifest.v1",
        "componentName": spec.name,
        "packageRoot": str(package_root) if package_root else f"/Game/Audio/{spec.name}",
        "roles": [{
            "role": "Sound",
            "file": role_name,
            "import": f"{spec.name}.sound.import.json",
            "sha1": _sha1(data),
        }],
        "generator": f"psap {__version__}",
    }
    (bundle / "handoff.manifest.json").write_text(
        json.dumps(handoff_manifest, indent=2, sort_keys=True))

    return {"dir": "handoff", "role": role_name, "manifest": "handoff.manifest.json"}

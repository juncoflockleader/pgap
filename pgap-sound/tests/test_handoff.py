"""S5: outputs + the unreal-mcp-rx audio source-handoff bundle."""

import json

from psap import generate

from .helpers import load_fixture


def test_write_outputs_and_manifest(tmp_path):
    spec = load_fixture("laser")
    manifest, buf = generate(spec, tmp_path)
    assert (tmp_path / "LaserZap.wav").exists()
    assert (tmp_path / "manifest.json").exists()
    assert manifest["files"][0]["role"] == "sound"
    assert manifest["specHash"] == spec.spec_hash()
    saved = json.loads((tmp_path / "manifest.json").read_text())
    assert saved["name"] == "LaserZap"


def test_handoff_bundle(tmp_path):
    spec = load_fixture("bark")
    manifest, _ = generate(spec, tmp_path, handoff=True)
    bundle = tmp_path / "handoff"
    assert (bundle / "S_DogBark.wav").exists()
    assert (bundle / "DogBark.sound.import.json").exists()
    hm = json.loads((bundle / "handoff.manifest.json").read_text())
    assert hm["schemaVersion"].startswith("game.interactive_component_agent_source_manifest")
    assert hm["roles"][0]["role"] == "Sound"
    assert hm["roles"][0]["file"] == "S_DogBark.wav"
    sidecar = json.loads((bundle / "DogBark.sound.import.json").read_text())
    assert sidecar["assetType"] == "SoundWave"

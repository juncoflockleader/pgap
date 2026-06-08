"""Surface treatments: per-surface base-color + normal-map synth (roadmap 1)."""

import json
from pathlib import Path

from pgap import nl
from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.texture import SURFACES, synth_textures

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _spec(surface=None):
    d = json.loads((FIX / "dog_golden_retriever.json").read_text())
    if surface is not None:
        d.setdefault("material", {})["surface"] = surface
    return Spec.from_dict(d)


def test_every_surface_emits_base_and_normal_png():
    for surface in SURFACES:
        tex = synth_textures(_spec(surface), make_rng(7))
        assert tex["baseColor"][:8] == b"\x89PNG\r\n\x1a\n", surface
        assert tex["normal"][:8] == b"\x89PNG\r\n\x1a\n", surface
        assert tex["surface"] == surface


def test_smooth_normal_is_flat_textured_is_not():
    smooth = synth_textures(_spec("smooth"), make_rng(7))["normal"]
    scales = synth_textures(_spec("scales"), make_rng(7))["normal"]
    # a textured surface produces a different (relief) normal map than flat smooth
    assert smooth != scales


def test_surface_is_deterministic():
    a = synth_textures(_spec("scales"), make_rng(7))
    b = synth_textures(_spec("scales"), make_rng(7))
    assert a["baseColor"] == b["baseColor"] and a["normal"] == b["normal"]


def test_unknown_surface_falls_back_to_smooth():
    tex = synth_textures(_spec("bogus"), make_rng(7))
    assert tex["surface"] == "smooth"


def test_dog_defaults_to_fur():
    assert synth_textures(_spec(), make_rng(7))["surface"] == "fur"


def test_surface_word_keyword_mapping():
    assert nl._surface_word("a scaly green dragon") == "scales"
    assert nl._surface_word("feathered wings") == "feathers"
    assert nl._surface_word("a chitinous carapace") == "chitin"
    assert nl._surface_word("rough bark skin") == "bark"
    assert nl._surface_word("a fluffy puppy") == "fur"
    assert nl._surface_word("a plain blue ball") is None


def test_nl_routes_surface_end_to_end():
    assert nl.prompt_to_spec("a scaly green dog")["material"].get("surface") == "scales"
    assert nl.prompt_to_spec("a fluffy white dog")["material"].get("surface") == "fur"

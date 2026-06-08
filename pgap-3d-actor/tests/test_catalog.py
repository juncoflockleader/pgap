"""Headless renderer + bestiary catalog generator (roadmap 2, L5)."""

import numpy as np

from pgap.catalog import build_catalog
from pgap.render import render_image
from pgap.rng import make_rng
from pgap.spec import Spec
from pgap.v2.assembly import build_actor
from pgap.v2.registry import TEMPLATE_REGISTRY, load_template


def _mesh(name="biped", h=180, coat="tan"):
    spec = Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": 5,
                           "triBudget": 9000, "proportions": {"heightCm": h},
                           "material": {"baseColor": coat}})
    return build_actor(load_template(name), spec, make_rng(spec.seed))[1]


def test_render_is_nonempty_and_deterministic():
    mesh = _mesh()
    a = render_image(mesh, size=64)
    b = render_image(mesh, size=64)
    assert a.shape == (64, 64, 3) and a.dtype == np.uint8
    assert np.array_equal(a, b)                       # pure numpy ⇒ byte-identical
    # the creature covers a meaningful share of the frame (not an empty render)
    bg = a[0, 0].astype(int)
    foreground = (np.abs(a.astype(int) - bg).sum(2) > 12).mean()
    assert foreground > 0.10, foreground


def test_tint_recovers_coat_color():
    mesh = _mesh()
    raw = render_image(mesh, size=64)
    tinted = render_image(mesh, size=64, tint=(0.80, 0.58, 0.30))   # golden coat
    assert not np.array_equal(raw, tinted)
    # the golden tint pushes the lit body warm (more red than blue on average)
    lit = tinted.reshape(-1, 3).astype(float)
    body = lit[(lit.sum(1) > 60)]                     # ignore background pixels
    assert body[:, 0].mean() > body[:, 2].mean()


def test_catalog_writes_gallery_and_is_deterministic(tmp_path):
    img, md = tmp_path / "bestiary", tmp_path / "BESTIARY.md"
    rows = build_catalog(img, md, size=48, templates=["biped", "dragon"])
    assert {r["name"] for r in rows} == {"biped", "dragon"}
    assert (img / "biped.png").exists() and (img / "dragon.png").exists()
    text = md.read_text()
    assert "# Bestiary" in text and "biped" in text and "dragon" in text
    assert 'src="bestiary/dragon.png"' in text       # relative image path resolved
    before = (img / "dragon.png").read_bytes()
    build_catalog(img, md, size=48, templates=["biped", "dragon"])
    assert (img / "dragon.png").read_bytes() == before


def test_catalog_renders_every_template(tmp_path):
    # L5 exit: the gallery renders *every* template (tiny size keeps it cheap).
    img, md = tmp_path / "b", tmp_path / "B.md"
    rows = build_catalog(img, md, size=16)
    assert {r["name"] for r in rows} == set(TEMPLATE_REGISTRY)
    for name in TEMPLATE_REGISTRY:
        assert (img / f"{name}.png").exists(), name
        assert name in md.read_text()

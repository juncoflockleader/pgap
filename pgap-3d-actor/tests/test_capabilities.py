"""M7/FR7: capability report + fail-closed spec validation."""

from __future__ import annotations

from pgap.capabilities import capability_report, validate_spec


def test_report_enumerates_support():
    r = capability_report()
    assert set(r["archetypes"]) == {"prop", "quadruped", "biped"}
    assert "dog" in r["speciesWithPartLibrary"]
    assert r["animationsByArchetype"]["biped"] == ["idle", "walk"]
    assert "tail_wag" in r["animationsByArchetype"]["quadruped"]
    assert "floppy" in r["traits"]["ears"] and "pointy" in r["traits"]["ears"]
    assert "golden" in r["coatKeywords"] and "stone" in r["coatKeywords"]


def test_valid_dog_passes():
    rep = validate_spec({"archetype": "quadruped", "species": "dog", "seed": 1})
    assert rep["ok"] and not rep["errors"]


def test_unsupported_archetype_fails_closed():
    rep = validate_spec({"archetype": "octopus", "species": "octopus", "seed": 1})
    assert rep["ok"] is False and rep["errors"]


def test_unknown_trait_clamped_with_warning():
    rep = validate_spec({"archetype": "quadruped", "species": "dog", "seed": 1,
                         "traits": {"ears": "gigantic"}})
    assert rep["ok"]
    assert rep["normalized"]["traits"]["ears"] == "floppy"  # default
    assert any("ears" in w for w in rep["warnings"])


def test_unavailable_animation_dropped():
    rep = validate_spec({"archetype": "biped", "species": "humanoid", "seed": 1,
                         "animations": ["idle", "tail_wag", "bark_pose"]})
    assert rep["normalized"]["animations"] == ["idle"]
    assert any("tail_wag" in w or "bark_pose" in w for w in rep["warnings"])


def test_out_of_range_proportion_clamped():
    rep = validate_spec({"archetype": "quadruped", "species": "dog", "seed": 1,
                         "proportions": {"legLength": 9.0}})
    assert rep["normalized"]["proportions"]["legLength"] == 2.0
    assert any("legLength" in w for w in rep["warnings"])


def test_unknown_species_warns_not_fails():
    rep = validate_spec({"archetype": "quadruped", "species": "chimera", "seed": 1})
    assert rep["ok"] and any("part library" in w for w in rep["warnings"])

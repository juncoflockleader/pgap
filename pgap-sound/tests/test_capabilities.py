"""S2: capability report + fail-closed validation."""

from psap.capabilities import CATEGORIES, capability_report, validate_spec

from .helpers import load_fixture


def test_report_shape():
    r = capability_report()
    assert r["schemaVersion"].startswith("psap.capabilities")
    for cat in CATEGORIES:
        assert cat in r["categories"]
    assert "laser" in r["sfxPresets"]
    assert "bark" in r["vocalPresets"]
    assert "square" in r["waves"]


def test_fixtures_validate():
    for name in ("laser", "coin", "bark", "roar", "metal_clang"):
        ok, errors = validate_spec(load_fixture(name).to_dict())
        assert ok, f"{name}: {errors}"


def test_fail_closed_unknown_category():
    ok, errors = validate_spec({"category": "music", "graph": {}})
    assert not ok and any("category" in e for e in errors)


def test_fail_closed_unknown_wave_and_fx():
    ok, _ = validate_spec({"category": "sfx", "sample_rate": 44100,
                           "graph": {"wave": "bogus"}})
    assert not ok
    ok2, _ = validate_spec({"category": "sfx", "sample_rate": 44100,
                            "graph": {"fx": ["reverb"]}})
    assert not ok2


def test_fail_closed_out_of_range():
    ok, _ = validate_spec({"category": "sfx", "sample_rate": 12345, "graph": {}})
    assert not ok
    ok2, _ = validate_spec({"category": "sfx", "sample_rate": 44100,
                            "duration_ms": 0, "graph": {}})
    assert not ok2
    ok3, _ = validate_spec({"category": "sfx", "sample_rate": 44100,
                            "gain_dbfs": 6.0, "graph": {}})
    assert not ok3

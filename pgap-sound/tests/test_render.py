"""S1: loudness-safe rendering — no clipping, peak normalized to target."""

import numpy as np

from psap.render import db_to_lin, finalize

from .helpers import load_fixture
from psap import render_spec


def test_no_clipping_even_with_hot_input():
    hot = np.sin(np.linspace(0, 400, 8000)) * 12.0  # wildly over unity
    out = finalize(hot, 44100, peak_dbfs=-1.0)
    assert np.max(np.abs(out)) <= 1.0


def test_peak_hits_target():
    sig = np.sin(np.linspace(0, 80, 6000))
    for target in (-1.0, -3.0, -6.0):
        out = finalize(sig, 44100, peak_dbfs=target)
        assert abs(np.max(np.abs(out)) - db_to_lin(target)) < 1e-6


def test_all_fixtures_loudness_safe():
    for name in ("laser", "coin", "bark", "roar"):
        buf = render_spec(load_fixture(name))
        assert np.max(np.abs(buf)) <= 1.0
        # peak normalized to the spec default (-1 dBFS) => clearly audible
        assert np.max(np.abs(buf)) > 0.5


def test_fades_remove_edge_clicks():
    buf = render_spec(load_fixture("laser"))
    assert abs(buf[0]) < 1e-3 and abs(buf[-1]) < 1e-3

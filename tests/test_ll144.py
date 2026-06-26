"""Tests for the NYC LL144 bias-audit MCP — selection rate, impact ratio (4/5ths), summary."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ll144", Path(__file__).resolve().parents[1] / "server.py")
srv = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(srv)


def test_no_adverse_impact_when_rates_equal():
    r = srv.run_bias_audit("sex", [{"group": "male", "selected": 50, "total": 100},
                                    {"group": "female", "selected": 50, "total": 100}])
    assert r.adverse_impact is False
    assert r.min_impact_ratio == 1.0
    assert all(not g.flagged for g in r.groups)
    assert r.sigil


def test_detects_adverse_impact_below_four_fifths():
    # female rate 30%, male 60% → impact ratio 0.5 < 0.80 → flagged
    r = srv.run_bias_audit("sex", [{"group": "male", "selected": 60, "total": 100},
                                    {"group": "female", "selected": 30, "total": 100}])
    assert r.adverse_impact is True
    assert r.most_selected_group == "male"
    fem = next(g for g in r.groups if g.group == "female")
    assert fem.impact_ratio == 0.5 and fem.flagged is True


def test_impact_ratio_at_threshold_not_flagged():
    # 0.80 exactly is NOT below 0.80
    r = srv.run_bias_audit("x", [{"group": "a", "selected": 100, "total": 100},
                                  {"group": "b", "selected": 80, "total": 100}])
    b = next(g for g in r.groups if g.group == "b")
    assert b.impact_ratio == 0.8 and b.flagged is False
    assert r.adverse_impact is False


def test_summary_overall_compliance():
    s = srv.generate_ll144_summary([
        {"category": "sex", "groups": [{"group": "m", "selected": 50, "total": 100}, {"group": "f", "selected": 48, "total": 100}]},
        {"category": "race", "groups": [{"group": "a", "selected": 40, "total": 100}, {"group": "b", "selected": 20, "total": 100}]},
    ], tool_name="HireBot", audit_date="2026-06-26")
    assert s["tool"] == "HireBot"
    assert s["overall_compliant"] is False  # race category has adverse impact (0.5)
    assert len(s["categories"]) == 2
    assert s["sigil"]


def test_check_compliance_gaps():
    c = srv.check_compliance(has_independent_audit=True)
    assert c["compliant"] is False
    assert "public summary of results published" in c["gaps"]
    full = srv.check_compliance(True, True, True, True)
    assert full["compliant"] is True and not full["gaps"]


def test_zero_total_safe():
    r = srv.run_bias_audit("x", [{"group": "a", "selected": 0, "total": 0}])
    assert r.groups[0].selection_rate == 0.0

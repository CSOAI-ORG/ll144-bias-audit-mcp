#!/usr/bin/env python3
"""
NYC Local Law 144 Bias-Audit MCP — CSOAI Layer-0.

NYC LL144 requires an INDEPENDENT annual bias audit of any Automated Employment
Decision Tool (AEDT), with a published summary, before use. This computes the
required metrics — selection rate + impact ratio per category (the 4/5ths rule) —
produces the public summary, and signs it (attestable). Recurring, legally-required.

Tools: run_bias_audit · generate_ll144_summary · check_compliance
"""
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

mcp = FastMCP("LL144 Bias Audit", instructions="NYC Local Law 144 AEDT bias audit — selection rate, impact ratio (4/5ths), public summary, signed.")

# ── SIGIL ──
import hashlib as _hl, time as _t, json as _j, os as _os
_SIGIL_LOG = _os.environ.get("SIGIL_LOG", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ll144_sigil.log"))
def _sigil(op, body):
    try:
        prev = ""
        if _os.path.exists(_SIGIL_LOG):
            with open(_SIGIL_LOG) as f:
                ls = f.readlines()
                if ls: prev = _j.loads(ls[-1]).get("digest", "")
        ts = int(_t.time()); dg = _hl.sha256(f"{op}|{ts}|{prev[:8]}|{body}".encode()).hexdigest()[:16]
        _os.makedirs(_os.path.dirname(_SIGIL_LOG), exist_ok=True)
        with open(_SIGIL_LOG, "a") as f: f.write(_j.dumps({"ts": ts, "op": op, "body": body, "prev_digest": prev, "digest": dg}) + "\n")
        return dg
    except Exception: return ""

FOUR_FIFTHS = 0.80  # EEOC adverse-impact threshold used by LL144


class GroupResult(BaseModel):
    group: str
    selected: int
    total: int
    selection_rate: float
    impact_ratio: float
    flagged: bool


class AuditResult(BaseModel):
    category: str
    groups: List[GroupResult] = Field(default_factory=list)
    most_selected_group: str = ""
    min_impact_ratio: float = 1.0
    adverse_impact: bool = False
    sigil: str = ""


def _audit_category(category: str, rows: List[Dict[str, Any]]) -> AuditResult:
    groups = []
    for r in rows:
        sel, tot = int(r.get("selected", 0)), int(r.get("total", 0))
        rate = (sel / tot) if tot else 0.0
        groups.append({"group": str(r.get("group", "?")), "selected": sel, "total": tot, "selection_rate": rate})
    base = max((g["selection_rate"] for g in groups), default=0.0)  # highest-selected group = reference
    most = next((g["group"] for g in groups if g["selection_rate"] == base), "")
    out = []
    min_ir = 1.0
    for g in groups:
        ir = (g["selection_rate"] / base) if base else 1.0
        ir = round(ir, 4)
        flagged = ir < FOUR_FIFTHS
        min_ir = min(min_ir, ir)
        out.append(GroupResult(group=g["group"], selected=g["selected"], total=g["total"],
                               selection_rate=round(g["selection_rate"], 4), impact_ratio=ir, flagged=flagged))
    return AuditResult(category=category, groups=out, most_selected_group=most,
                       min_impact_ratio=round(min_ir, 4), adverse_impact=min_ir < FOUR_FIFTHS,
                       sigil=_sigil("LL144", f"{category}|{len(out)}"))


@mcp.tool()
def run_bias_audit(category: str, groups: List[Dict[str, Any]]) -> AuditResult:
    """Run the LL144 bias audit for one category (e.g. 'sex', 'race/ethnicity', or an intersectional category).
    groups: [{group, selected, total}]. Returns selection rate + impact ratio per group; flags any impact ratio < 0.80 (4/5ths rule)."""
    return _audit_category(category, groups)


@mcp.tool()
def generate_ll144_summary(audits: List[Dict[str, Any]], tool_name: str = "AEDT", audit_date: str = "") -> Dict[str, Any]:
    """Produce the LL144 public summary from one or more category audits.
    audits: [{category, groups:[{group, selected, total}]}]. Returns the publishable summary + overall compliance."""
    results = [_audit_category(a.get("category", "category"), a.get("groups", [])) for a in audits]
    any_adverse = any(r.adverse_impact for r in results)
    return {
        "tool": tool_name,
        "audit_date": audit_date or "(set audit_date)",
        "standard": "NYC Local Law 144 (AEDT bias audit)",
        "metric": "selection rate + impact ratio (4/5ths / 0.80 threshold)",
        "categories": [r.model_dump() for r in results],
        "overall_compliant": not any_adverse,
        "disclosure": "This summary must be published on the employer's website before AEDT use, and a candidate notice provided (LL144).",
        "sigil": _sigil("LL144", f"summary|{tool_name}|{len(results)}"),
    }


@mcp.tool()
def check_compliance(has_independent_audit: bool = False, summary_published: bool = False, candidate_notice: bool = False, audit_within_12_months: bool = False) -> Dict[str, Any]:
    """Check the LL144 procedural requirements (independent audit, published summary, candidate notice, audit within 12 months)."""
    checks = {
        "independent bias audit performed": has_independent_audit,
        "public summary of results published": summary_published,
        "candidate/employee notice (>=10 business days)": candidate_notice,
        "audit within the last 12 months": audit_within_12_months,
    }
    gaps = [k for k, v in checks.items() if not v]
    return {"compliant": not gaps, "checks": checks, "gaps": gaps,
            "note": "LL144 is enforced by NYC DCWP; penalties accrue per violation per day. Annual re-audit required."}


def main():
    mcp.run()


if __name__ == "__main__":
    main()

# ll144-bias-audit-mcp

**NYC Local Law 144** requires an independent **annual bias audit** of any Automated Employment Decision Tool (AEDT), with a published summary, before use. This computes the required metrics and signs the result. CSOAI Layer-0.

## Tools
- `run_bias_audit(category, groups)` — selection rate + impact ratio per group; flags impact ratio < 0.80 (4/5ths rule)
- `generate_ll144_summary(audits, tool_name, audit_date)` — the publishable summary + overall compliance
- `check_compliance(...)` — the procedural requirements (independent audit, published summary, candidate notice, ≤12 months)

Recurring, legally-required (DCWP-enforced). Apache-2.0.

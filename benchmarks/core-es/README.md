# Benchmark Suite: core-es

This suite is a lightweight regression pack for CI.
- Backend: `mock`
- Purpose: schema + pipeline + store + report integration stability
- Cases: `case01` (pm4sand), `case02` (pm4silt + rigid), `case03` (mixed + scale_to_pga)
- Golden file stores metric-level checks (`pga`, `ru_max`) with explicit tolerances.
- Additional checks: physical `ru` bounds and deterministic repeat-signature verification.
- Time-step sensitivity check: optional per-case `dt_sensitivity.threshold` (Δt vs Δt/2 PSA diff).

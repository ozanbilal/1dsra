# core-eql benchmark suite

This suite validates the native equivalent-linear backend (`solver_backend: eql`)
for MKZ/GQH strain-compatible iteration behavior.

Coverage targets:
- nonlinear-compatible MKZ/GQH profile support without OpenSees
- deterministic rerun signatures
- dt sensitivity checks
- transfer-function output consistency

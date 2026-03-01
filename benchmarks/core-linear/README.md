# core-linear benchmark suite

This suite validates the native linear SH backend (`solver_backend: linear`) with
deterministic case outputs and transfer-function metrics.

Coverage targets:
- baseline linear run stability
- deterministic repeat signature
- dt sensitivity check
- transfer function outputs (`transfer_abs_max`, `transfer_peak_freq_hz`)

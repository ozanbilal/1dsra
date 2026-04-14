from __future__ import annotations

from pathlib import Path

import numpy as np

from dsra1d.post.layer_response import LayerResponseHistory, write_layer_response_outputs


def test_write_layer_response_outputs_preserves_kpa_scale(tmp_path: Path) -> None:
    history = LayerResponseHistory(
        layer_index_zero_based=0,
        layer_tag=1,
        layer_name="Layer-1",
        z_mid_m=2.0,
        strain=np.array([0.0, 1.0e-4, -1.0e-4], dtype=np.float64),
        stress_kpa=np.array([0.0, 45.0, -42.0], dtype=np.float64),
        gamma_max=1.0e-4,
        tau_peak_kpa=45.0,
        secant_g_kpa=4.5e5,
        secant_g_over_gmax=0.8,
    )

    out_files, summary_path = write_layer_response_outputs(
        tmp_path,
        time_s=np.array([0.0, 0.1, 0.2], dtype=np.float64),
        histories=[history],
    )

    assert summary_path is not None and summary_path.exists()
    assert len(out_files) == 2

    stress_out = np.loadtxt(tmp_path / "layer_1_stress.out")
    assert stress_out.shape == (3, 2)
    assert stress_out[1, 1] == 45.0

    lines = summary_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    parts = lines[1].split(",")
    assert float(parts[5]) == 45.0
    assert float(parts[6]) == 4.5e8
    assert float(parts[7]) == 0.8

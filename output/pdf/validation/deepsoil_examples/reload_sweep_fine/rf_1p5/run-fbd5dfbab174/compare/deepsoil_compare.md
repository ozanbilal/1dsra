# DEEPSOIL Comparison: run-fbd5dfbab174

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\reload_sweep_fine\rf_1p5\run-fbd5dfbab174`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `5.958626` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.330074`
- PGA diff: `-66.993` %
- Surface RMSE: `7.880005` m/s^2
- Surface NRMSE: `0.436507`
- Surface correlation: `-0.000494`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.863217` m/s^2
- PSA NRMSE: `0.193978`
- PSA max abs diff: `32.907074` m/s^2
- PSA diff at reference peak: `-81.178` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

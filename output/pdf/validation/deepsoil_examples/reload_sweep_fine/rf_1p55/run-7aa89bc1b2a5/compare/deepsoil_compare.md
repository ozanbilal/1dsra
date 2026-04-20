# DEEPSOIL Comparison: run-7aa89bc1b2a5

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\reload_sweep_fine\rf_1p55\run-7aa89bc1b2a5`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `6.174067` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.342008`
- PGA diff: `-65.799` %
- Surface RMSE: `7.883376` m/s^2
- Surface NRMSE: `0.436694`
- Surface correlation: `-0.000321`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.882549` m/s^2
- PSA NRMSE: `0.194455`
- PSA max abs diff: `32.736832` m/s^2
- PSA diff at reference peak: `-80.759` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

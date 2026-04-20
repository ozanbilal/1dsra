# DEEPSOIL Comparison: run-512207e16c0b

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\reload_sweep_fine\rf_1p65\run-512207e16c0b`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `6.607369` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.366011`
- PGA diff: `-63.399` %
- Surface RMSE: `7.891454` m/s^2
- Surface NRMSE: `0.437142`
- Surface correlation: `-0.001687`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.898042` m/s^2
- PSA NRMSE: `0.194837`
- PSA max abs diff: `32.211860` m/s^2
- PSA diff at reference peak: `-79.463` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

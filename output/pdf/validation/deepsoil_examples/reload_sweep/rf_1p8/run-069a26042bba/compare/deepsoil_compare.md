# DEEPSOIL Comparison: run-069a26042bba

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\reload_sweep\rf_1p8\run-069a26042bba`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `7.111540` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.393939`
- PGA diff: `-60.606` %
- Surface RMSE: `7.904278` m/s^2
- Surface NRMSE: `0.437852`
- Surface correlation: `-0.003824`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.971777` m/s^2
- PSA NRMSE: `0.196656`
- PSA max abs diff: `31.859774` m/s^2
- PSA diff at reference peak: `-78.595` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

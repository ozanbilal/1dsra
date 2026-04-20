# DEEPSOIL Comparison: run-772bd63dd52e

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\gammaref_sweep\scale_1p3\run-772bd63dd52e`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `7.323760` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.405695`
- PGA diff: `-59.431` %
- Surface RMSE: `7.910565` m/s^2
- Surface NRMSE: `0.438200`
- Surface correlation: `-0.002177`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.983972` m/s^2
- PSA NRMSE: `0.196957`
- PSA max abs diff: `31.162289` m/s^2
- PSA diff at reference peak: `-76.874` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

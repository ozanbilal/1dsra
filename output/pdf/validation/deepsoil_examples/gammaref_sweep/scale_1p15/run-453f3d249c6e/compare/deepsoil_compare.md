# DEEPSOIL Comparison: run-453f3d249c6e

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\gammaref_sweep\scale_1p15\run-453f3d249c6e`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `6.694505` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.370837`
- PGA diff: `-62.916` %
- Surface RMSE: `7.892537` m/s^2
- Surface NRMSE: `0.437202`
- Surface correlation: `-0.001632`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.917173` m/s^2
- PSA NRMSE: `0.195309`
- PSA max abs diff: `32.180506` m/s^2
- PSA diff at reference peak: `-79.386` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

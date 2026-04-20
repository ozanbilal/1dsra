# DEEPSOIL Comparison: run-efe74cb2f902

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_elastic_dt0025_v2\stratawave\run-efe74cb2f902`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `6.486735` m/s^2
- PGA (DEEPSOIL): `18.031400` m/s^2
- PGA ratio: `0.359747`
- PGA diff: `-64.025` %
- Surface RMSE: `7.905858` m/s^2
- Surface NRMSE: `0.438449`
- Surface correlation: `0.000426`

## PSA
- PSA points compared: `80`
- PSA RMSE: `8.404784` m/s^2
- PSA NRMSE: `0.207408`
- PSA max abs diff: `29.973982` m/s^2
- PSA diff at reference peak: `-73.968` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

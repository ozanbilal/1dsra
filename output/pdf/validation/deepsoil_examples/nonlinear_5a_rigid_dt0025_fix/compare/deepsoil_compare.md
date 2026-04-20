# DEEPSOIL Comparison: run-ebbfd5c09c7e

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid_dt0025_fix\stratawave\run-ebbfd5c09c7e`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `7.735940` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.428527`
- PGA diff: `-57.147` %
- Surface RMSE: `7.923364` m/s^2
- Surface NRMSE: `0.438909`
- Surface correlation: `-0.003206`

## PSA
- PSA points compared: `80`
- PSA RMSE: `8.135214` m/s^2
- PSA NRMSE: `0.200688`
- PSA max abs diff: `30.623342` m/s^2
- PSA diff at reference peak: `-75.545` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

# DEEPSOIL Comparison: run-fd7cd62f42c9

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid_dt0025\stratawave\run-fd7cd62f42c9`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00500000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `9597`
- PGA (StrataWave): `5.533130` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.306504`
- PGA diff: `-69.350` %
- Surface RMSE: `8.039472` m/s^2
- Surface NRMSE: `0.445341`
- Surface correlation: `0.005131`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.608714` m/s^2
- PSA NRMSE: `0.187699`
- PSA max abs diff: `30.889601` m/s^2
- PSA diff at reference peak: `-76.202` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.005s, DEEPSOIL=0.02s).
- Surface records have different end times; check truncation/windowing.

# DEEPSOIL Comparison: run-2c397754b1e4

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_elastic_dt005\stratawave\run-2c397754b1e4`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00500000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `9597`
- PGA (StrataWave): `5.798578` m/s^2
- PGA (DEEPSOIL): `18.031400` m/s^2
- PGA ratio: `0.321582`
- PGA diff: `-67.842` %
- Surface RMSE: `7.913425` m/s^2
- Surface NRMSE: `0.438869`
- Surface correlation: `0.000637`

## PSA
- PSA points compared: `80`
- PSA RMSE: `8.467833` m/s^2
- PSA NRMSE: `0.208964`
- PSA max abs diff: `34.308935` m/s^2
- PSA diff at reference peak: `-84.666` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.005s, DEEPSOIL=0.02s).

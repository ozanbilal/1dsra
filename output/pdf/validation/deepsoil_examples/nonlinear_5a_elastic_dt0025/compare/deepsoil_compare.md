# DEEPSOIL Comparison: run-efe74cb2f902

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_elastic_dt0025\stratawave\run-efe74cb2f902`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `5.797736` m/s^2
- PGA (DEEPSOIL): `18.031400` m/s^2
- PGA ratio: `0.321536`
- PGA diff: `-67.846` %
- Surface RMSE: `7.842525` m/s^2
- Surface NRMSE: `0.434937`
- Surface correlation: `-0.001028`

## PSA
- PSA points compared: `80`
- PSA RMSE: `8.434162` m/s^2
- PSA NRMSE: `0.208133`
- PSA max abs diff: `33.871517` m/s^2
- PSA diff at reference peak: `-83.586` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

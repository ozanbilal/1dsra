# DEEPSOIL Comparison: run-d6191cf4d93e

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\gammaref_sweep\scale_0p85\run-d6191cf4d93e`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `3.921998` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.217256`
- PGA diff: `-78.274` %
- Surface RMSE: `7.865862` m/s^2
- Surface NRMSE: `0.435724`
- Surface correlation: `0.000515`

## PSA
- PSA points compared: `80`
- PSA RMSE: `8.127951` m/s^2
- PSA NRMSE: `0.200508`
- PSA max abs diff: `33.200779` m/s^2
- PSA diff at reference peak: `-81.903` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

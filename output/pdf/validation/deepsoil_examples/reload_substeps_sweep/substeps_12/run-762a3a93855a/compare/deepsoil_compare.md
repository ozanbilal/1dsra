# DEEPSOIL Comparison: run-762a3a93855a

## Inputs
- StrataWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\reload_substeps_sweep\substeps_12\run-762a3a93855a`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\surface.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\deepsoil_examples\nonlinear_5a_rigid\deepsoil_ref\psa.csv`

## Surface Acceleration
- StrataWave dt: `0.00250000` s
- DEEPSOIL dt: `0.02000000` s
- Overlap duration: `47.9800` s
- Overlap samples: `19193`
- PGA (StrataWave): `5.703107` m/s^2
- PGA (DEEPSOIL): `18.052400` m/s^2
- PGA ratio: `0.315920`
- PGA diff: `-68.408` %
- Surface RMSE: `7.877333` m/s^2
- Surface NRMSE: `0.436359`
- Surface correlation: `-0.001525`

## PSA
- PSA points compared: `80`
- PSA RMSE: `7.860992` m/s^2
- PSA NRMSE: `0.193923`
- PSA max abs diff: `32.948314` m/s^2
- PSA diff at reference peak: `-81.280` %
- Reference peak period: `0.0500` s

## Warnings
- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).

# Boundary Audit

- Profile: deepsoil_gqh_5layer_baseline geometry with explicit bedrock Vs=760 m/s, unit weight=25 kN/m3, damping_ratio=0.02
- Motion: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\examples\motions\sample_motion.csv`

## Cases
### `rigid_outcrop`
- boundary: `rigid`
- input_type: `outcrop`
- raw input PGA: `0.020000` m/s^2
- applied input PGA: `0.010000` m/s^2
- surface PGA: `0.016417` m/s^2
- max surface PSA: `0.041722` m/s^2
- surface peak period: `0.050000` s
- max applied input PSA: `0.020056` m/s^2
- surface/input PSA ratio: `2.080242`

### `rigid_within`
- boundary: `rigid`
- input_type: `within`
- raw input PGA: `0.020000` m/s^2
- applied input PGA: `0.020000` m/s^2
- surface PGA: `0.032285` m/s^2
- max surface PSA: `0.083364` m/s^2
- surface peak period: `0.050000` s
- max applied input PSA: `0.040113` m/s^2
- surface/input PSA ratio: `2.078248`

### `elastic_halfspace_outcrop`
- boundary: `elastic_halfspace`
- input_type: `outcrop`
- raw input PGA: `0.020000` m/s^2
- applied input PGA: `0.020000` m/s^2
- surface PGA: `0.037353` m/s^2
- max surface PSA: `0.092303` m/s^2
- surface peak period: `0.050000` s
- max applied input PSA: `0.040113` m/s^2
- surface/input PSA ratio: `2.301103`

## Comparisons

### `elastic_vs_rigid_outcrop`
- surface PGA ratio: `2.275244`
- max surface PSA ratio: `2.212341`
- applied input PGA ratio: `2.000000`
- surface peak period diff: `0.000000` %

### `elastic_outcrop_vs_rigid_within`
- surface PGA ratio: `1.156958`
- max surface PSA ratio: `1.107232`
- applied input PGA ratio: `1.000000`
- surface peak period diff: `0.000000` %
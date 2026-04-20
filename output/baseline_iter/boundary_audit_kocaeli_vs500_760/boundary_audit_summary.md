# Boundary Audit

- Profile: deepsoil_gqh_5layer_baseline geometry with explicit bedrock Vs=760 m/s, unit weight=25 kN/m3, damping_ratio=0.02
- Motion: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\bundle_primary\input_motion.csv`

## Cases
### `rigid_outcrop`
- boundary: `rigid`
- input_type: `outcrop`
- raw input PGA: `2.146778` m/s^2
- applied input PGA: `1.073390` m/s^2
- surface PGA: `2.615135` m/s^2
- max surface PSA: `13.254381` m/s^2
- surface peak period: `0.189288` s
- max applied input PSA: `3.788460` m/s^2
- surface/input PSA ratio: `3.498620`

### `rigid_within`
- boundary: `rigid`
- input_type: `within`
- raw input PGA: `2.146778` m/s^2
- applied input PGA: `2.146780` m/s^2
- surface PGA: `3.729025` m/s^2
- max surface PSA: `17.677967` m/s^2
- surface peak period: `0.189288` s
- max applied input PSA: `7.576919` m/s^2
- surface/input PSA ratio: `2.333134`

### `elastic_halfspace_outcrop`
- boundary: `elastic_halfspace`
- input_type: `outcrop`
- raw input PGA: `2.146778` m/s^2
- applied input PGA: `2.146780` m/s^2
- surface PGA: `4.683999` m/s^2
- max surface PSA: `17.341767` m/s^2
- surface peak period: `0.200085` s
- max applied input PSA: `7.576919` m/s^2
- surface/input PSA ratio: `2.288762`

## Comparisons

### `elastic_vs_rigid_outcrop`
- surface PGA ratio: `1.791112`
- max surface PSA ratio: `1.308380`
- applied input PGA ratio: `2.000000`
- surface peak period diff: `5.703592` %

### `elastic_outcrop_vs_rigid_within`
- surface PGA ratio: `1.256092`
- max surface PSA ratio: `0.980982`
- applied input PGA ratio: `1.000000`
- surface peak period diff: `5.703592` %

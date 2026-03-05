# Release Signoff Checklist

This checklist is the operational gate for `v*` tags.

## Machine-checked (must pass)
- Dedicated parity runner job completed (`self-hosted, linux, x64, opensees`)
- `1dsra campaign --suite release-signoff` passed
- `campaign_summary.json` contains `policy.campaign.passed=true`
- `campaign_summary.json` contains `signoff.passed=true` when generated with `--strict-signoff`
- Backend fingerprint check passed (required in release path; matrix value and observed run sha256 must match exactly)
- `python scripts/check_fingerprint_alignment.py --expected-sha <DSRA1D_CI_OPENSEES_SHA256>` passed
- `python scripts/check_release_signoff.py --campaign-dir <dir> --require-fingerprint` passed
- `signoff.conditions.backend_probe_not_assumed=true` and `signoff.observed.backend_probe_assumed_available=false`
- Changelog/tag checks passed

## Human-reviewed (must be confirmed)
- `SCIENTIFIC_CONFIDENCE_MATRIX.md` updated with latest verification date and confidence tier
- Repository variable `DSRA1D_CI_OPENSEES_SHA256` equals `benchmarks/policies/release_signoff.yml:opensees_fingerprint`
- PM4 calibration notes reviewed and consistent with strict/strict_plus validation ranges
- Release notes include known limitations and unsupported production scenarios

## Evidence artifacts
- `benchmark_release-signoff.json`
- `verify_batch_report.json`
- `campaign_summary.json`
- `campaign_summary.md`
- OpenSees parity artifacts from dedicated runner

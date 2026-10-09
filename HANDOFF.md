# HANDOFF

## Goal

Ship PanganLens as a strong, honest, inspectable data engineering portfolio. A publicly hosted preview is distinct from a live food-price data product.

## Source-of-truth recovery

- GitHub canonical source: https://github.com/Fadhilstat/PanganLens.
- GitLab target: https://gitlab.com/fadhilrusydih/panganlens.
- Verified initial shared contents at GitHub SHA 6a731b14c4c4944b35ee35834cff399d5e543544 and GitLab SHA a4cfb5fcf7cd89132af36e2e4777f31048e5baad. Histories differ but all 149 file blob SHA values matched.
- Retrieve fresh branch refs before writing: earlier SHAs are checkpoints, not permanent HEADs.
- Cloud readiness is separate and tracked in GitHub issue #48. Never publish guessed live prices.

## Portfolio preview scope

- Plain HTML/CSS/JS site serves a guarded production snapshot. As long as the snapshot is empty, the dashboard shows honest unavailable states.
- Independent calculator accepts four visitor-entered amounts for movement and regional differences. It never reads external price data or sends input to a server.
- Site includes an architecture summary and source link. README and docs/portfolio_case_study.md explain data pipeline, evidence, decisions, risk and remaining gaps.
- Tests run in GitHub Actions and GitLab CI without VPS. GitLab Pages should deploy website/ only after Python and Node verify stages succeed on the default branch.
- GitLab project Pages access control was private at last inspection. Public access requires checking the GitLab project's Pages setting and the deployed URL.

## Release method

1. Confirm working branch and source HEAD on GitHub. No force push.
2. Inspect changed files and execute Node math tests, Python tests, lint and CI.
3. With owner APPROVE PUSH and APPROVE MERGE, push feature branch and merge only after checks pass.
4. Fetch exact changed files from merged GitHub main, apply to a new GitLab feature branch, run MR pipeline, and merge only on success. Do not rewrite GitLab's different commit ancestry.
5. Compare GitHub and GitLab file path and blob SHA parity after merge.
6. Check the actual GitLab Pages deployment and anonymous access. Do not invent Pages domain or claim public reachability without verification.
7. Retain GCP and production data quality gates independently.

Rollback: revert the portfolio UI and CI Pages changes through reviewed pull/merge requests. No warehouse state or live snapshot is touched.

NEXT_ACTION: Complete CI-gated GitHub and GitLab PR/MR releases for the portfolio preview and check the real static-site deployment/access state.

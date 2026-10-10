# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phase: 2 Technical Implementation / 3 Repository / 4 Portfolio Preview
Milestone: Analytical semantics hardening for public portfolio
Status: RELEASE_CANDIDATE_NOT_YET_MERGED

## Verified baseline

- Canonical GitHub main: 761b6eebc9dfc848785e6d0e326ef06d06d9d068
- GitLab main: 590bada6cf6d270bc126bf4de5681967c8bf8de1
- At the last release, file-content parity was 153/153 while Git histories differed due to initial snapshot import.
- GitLab pipeline 2931802651: SUCCESS, including Pages deployment.
- GitLab project is public, but Pages access level private (checked again 2026-10-10).
- GitHub Pages is not enabled: last workflow 37974862397 failed Configure Pages with HTTP 404.
- Source price JSON remains empty; no verified public price data. GitHub issue #48 remains the cloud activation checkpoint.

## Candidate changes

- New browser/Node module website/dashboard_metrics.js for signed movers and missing-safe province ranks.
- New Node unit tests tests/dashboard_metrics.test.cjs.
- Integrate validated metric selection in website/app.js, with nonnumeric/zero prices excluded from movement and trend displays.
- Update index.html script order, GitHub and GitLab frontend CI tests, UX contract tests, and case-study documentation.
- Keep static preview as a portfolio sample, never pretend production prices are live.
- No VPS, no service credentials, no BigQuery writes, no production deployment configuration changes.

## Validation

- Local Node tests for new metric module: PASS (9/9).
- Git blob SHA parity of tested metric module and tests with candidate GitHub tree: PASS.
- GitHub integrated CI: NOT_RUN on new candidate.
- GitLab integrated CI and Pages: NOT_RUN on new candidate.
- Live browser visual QA: NOT_RUN.
- Anonymous Pages access: NOT_VERIFIED due to private Pages setting.
- Owner approval: user explicitly granted APPROVE PUSH and APPROVE MERGE for this continuation.
- Merge still requires a reviewed diff and green CI on each platform.

NOW: CI-gated release of the candidate on GitHub then GitLab, with full blob parity.
NEXT: Owner makes GitLab Pages viewable by everyone and verifies real public URL from Deploy > Pages.
LATER: Complete GCP activation Issue #48 and publish first reviewed curated dataset.
OPTIONAL: Browser E2E and accessibility testing on public URL.

NEXT_ACTION: Push candidate to one GitHub PR, verify CI and merge; mirror changed files to one GitLab MR, verify CI and merge; recheck Pages visibility and public URL.

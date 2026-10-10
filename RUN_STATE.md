# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phases: Technical implementation, repository, and portfolio preview
Milestone: End-to-end fail-closed public snapshot publication
Status: RELEASE_CANDIDATE_AWAITING_CI

## Verified latest baseline

- GitHub canonical main SHA: 0d9f668ecd2a1c0a0152c554afe07a67f2b700a8
- GitLab main SHA: 4843ec71c3f20cac6b6cd76bffcae26995fd39c9
- Previous GitHub PR #69 and GitLab MR !4: MERGED after green CI.
- GitLab main pipeline #2932618806: SUCCESS for Python, frontend, and static Pages.
- Previous release GitHub and GitLab trees: 155/155 matching blob SHA values; commit histories differ.
- GitLab project visibility: public; Pages access: private, verified again 2026-10-10.
- GitHub Pages remained disabled when last deployment was checked.
- Checked-in dashboard data remains empty and publish_state null; cloud activation tracked in GitHub Issue #48.

## Current candidate and evidence

- Exporter accepts only an active successful publish pointer with a valid date and reviewed freshness label.
- No active pointer: zero price queries, empty published rows; invalid pointer: fail before writing.
- National prices bounded by pointer date, provincial prices restricted to pointer date.
- Static Pages artifacts checked for JSON schema and publication metadata in both CI configurations.
- Browser blocks incompatible, unsigned or missing publication metadata and clears unavailable prices.
- Unit tests expanded in Python and Node; integrated GitHub/GitLab pipelines NOT_RUN at this checkpoint.
- Public Pages reachability, browser screenshot QA, and production BigQuery: NOT_VERIFIED.
- No VPS, secret, server, new production dataset, or new cloud role.

## Release and owner action

User granted APPROVE PUSH and APPROVE MERGE in this turn. Use one reviewed GitHub feature branch/PR, merge only after all GitHub quality jobs pass. Transfer exact reviewed changes to one GitLab MR, merge only after CI passes; then compare file paths and blob hashes. Verify GitLab main Pages deployment without claiming anonymous access.

NOW: Finish GitHub and GitLab CI-gated release.
NEXT: Owner changes GitLab Pages access to Everyone with access, then verify actual Pages URL without login.
LATER: Complete the separate BigQuery activation gate (#48) and publish first validated source snapshot.
OPTIONAL: Browser screenshot and accessibility audit after public Pages URL is reachable.

NEXT_ACTION: Verify exact PR/MR CI and content parity, then enable anonymous GitLab Pages access using owner settings.

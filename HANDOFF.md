# HANDOFF

## Product and working contracts

PanganLens Indonesia is a public food-price intelligence project. PIHPS Bank Indonesia is the preferred source while guarded source health and schema checks hold. The repository models ingestion, canonical mappings, quality gates, BigQuery curated marts, and a static public website snapshot. Do not show invented production values when the validated snapshot is absent.

Phase 2 is open. The existing GitHub issue `Fadhilstat/PanganLens#48` defines the separate cloud activation checklist and is not solved by this CI milestone. The current checked-in website snapshot is empty: `national_prices=[]`, `province_prices=[]`, and `publish_state=null`.

## GitLab CI quality parity milestone

Add a GitLab-only repository quality workflow using hosted CI. Keep the GitHub WIF and snapshot publication boundaries unchanged. GitHub remains the only verified PanganLens repository as of this checkpoint; an actual GitLab target has not been located in the connected account. Do not import or overwrite another repository in order to fill this gap.

The proposed `.gitlab-ci.yml` runs pytest, Ruff, and Python compilation using the existing `constraints/ci.txt` dependency pins. It runs on merge requests and default-branch updates only, has no GCP credentials, and cannot publish or ingest data. See `docs/gitlab_ci_parity.md` for acceptance and rollback rules.

## How to resume

1. Verify the current GitHub branch, PR, CI, and default-branch HEAD against live repository history. The baseline SHA in `RUN_STATE.md` is a checkpoint, not a merge target.
2. The user granted `APPROVE PUSH` and `APPROVE MERGE` on 2026-10-10 for this milestone. The merger must still verify green CI and a reviewed diff.
3. Locate the intended GitLab project, or obtain a separate decision about creating one, without overwriting a different repository or guessing history.
4. When a GitLab target exists, verify its base and run GitLab CI lint and a real MR pipeline before claiming GitLab parity.
5. Do not perform VPS, GCP activation, or production deployment in this continuation.

Unverified: GitLab repository identity, shared remote ancestry, new candidate GitLab pipeline result, production data readiness.

NEXT_ACTION: Verify the GitHub PR merge and CI, then locate the approved GitLab PanganLens destination for separate MR validation.

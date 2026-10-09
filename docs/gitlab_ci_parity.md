# GitLab CI quality mirror for PanganLens

## Purpose

GitLab can run the same repository-level Python quality checks as GitHub Actions without a VPS or a self-hosted runner. This is a CI portability milestone, not a change in data ownership, cloud identity, deployment, or production readiness.

The reviewed GitHub source baseline is `Fadhilstat/PanganLens` at `main` commit `c97ea82a3fb7308e93a49fdcfd8bb717911d3dce`, verified on 10 October 2026. At that checkpoint, no PanganLens project appeared among the authenticated GitLab user's project memberships. Do not assume a GitLab repository or a common Git history exists until each is explicitly verified.

## Contract and acceptance checks

| ID | Requirement | Evidence in this candidate | Acceptance |
| --- | --- | --- | --- |
| REQ-CI-001 | Run Python quality without a VPS | `.gitlab-ci.yml` on GitLab-hosted runners | GitLab MR pipeline passes after an approved push |
| REQ-CI-002 | Reuse the existing test commands | `tests/test_gitlab_ci_contract.py` | CI contract tests pass |
| REQ-CI-003 | Fail closed on cloud privilege | GitLab job has no WIF, GCP variable, deployment, or ingest step | Reviewed diff and CI configuration stay credential-free |
| REQ-CI-004 | Avoid unreviewed writes | Remote work remains approval-gated | Only the approved branch is pushed; merge needs a separate approval |

The GitLab job executes these commands from the repository root:

```sh
python -m pip install -c constraints/ci.txt -e ".[dev]"
pytest -q
ruff check src scripts tests
python -m compileall -q src scripts tests
```

These are the same four checks used by the verified GitHub `quality.yml` unit-test job. GitLab pipelines are limited to merge requests and the default branch. The GitLab job uses a Python 3.11 Docker image and the existing reviewed dependency constraints. The image tag tracks upstream security updates and is not immutable; pin a verified digest in a separate reviewed change if immutable image provenance becomes necessary.

## Intentional exclusions

- No new cloud resource, GCP authentication, BigQuery role, or secret.
- No CI-driven data ingestion, snapshot refresh, or publication.
- No GitLab Pages, GitHub Pages, Vercel, or VPS deployment in this milestone.
- No remote mirroring, import, force push, or overwrite of divergent histories.
- No new scheduled jobs or live PIHPS probes on GitLab. The pre-existing GitHub live probe remains a separate source-health check, not evidence that GitLab CI is green.

GitHub Issue #48 is still the cloud activation checkpoint. The repository's website snapshot remains empty until independent data publication gates pass. GitLab CI must not silently weaken those rules.

## Safe release sequence

1. Identify the intended GitLab PanganLens project and confirm its owner, branch, and history. If it does not exist, plan explicit creation only after owner approval.
2. Compare the exact GitHub and GitLab base commit trees. Resolve mismatches before copying any file; never assume their `main` branches are aligned.
3. Apply the reviewed patch to a single feature branch without overwriting uncommitted work.
4. Run local checks on a full checkout with dependencies installed, then push only after `APPROVE PUSH`.
5. Validate the GitLab CI syntax through GitLab CI Lint and verify the actual hosted MR pipeline. Treat local YAML parsing as a syntax smoke check, not a full GitLab validation.
6. Review diff and pipeline results. Merge only after a separate `APPROVE MERGE`.
7. Confirm the exact resulting commit on each intended remote. Do not call a mirror synchronized until SHA or an equivalent reviewed commit/tree comparison proves it.

## Rollback

The milestone adds isolated CI and documentation files. Remove the CI file on an approved branch to disable its jobs if GitLab validation identifies issues. Keep the last verified default-branch SHA. No warehouse or production data rollback is necessary because the change does not touch them.

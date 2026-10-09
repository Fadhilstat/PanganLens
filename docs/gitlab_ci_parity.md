# GitLab CI quality mirror for PanganLens

## Status (10 October 2026)

The GitHub milestone was released through [PR #64](https://github.com/Fadhilstat/PanganLens/pull/64). The verified GitHub main commit is 9005b2a5fc5baa7b9e45a6cda552095b6b8b8349. [GitHub Actions run #37970221878](https://github.com/Fadhilstat/PanganLens/actions/runs/37970221878) succeeded. The connected GitLab account has no authorized PanganLens project, so GitLab pipeline and commit parity are NOT_VERIFIED.

GitLab can run Python repository quality checks using hosted CI without a VPS. This is CI portability, not production BigQuery activation or data publication.

## Quality contract

| Requirement | GitHub evidence | Required GitLab proof |
| --- | --- | --- |
| REQ-CI-001: Hosted Python CI | CI file merged in PR #64 | A successful GitLab pipeline |
| REQ-CI-002: Same dependency constraints and checks | Python quality job succeeded | Matching pytest, Ruff, and compile jobs |
| REQ-CI-003: No cloud or deployment authority | GitLab CI file excludes cloud credentials and deploy steps | Review effective CI configuration |
| REQ-CI-004: No destructive sync | GitHub main verified | Approved target, matching history/tree, no force push |

The GitLab CI job uses Python 3.11 and the reviewed dependency constraints. Its commands are:

    python -m pip install -c constraints/ci.txt -e ".[dev]"
    pytest -q
    ruff check src scripts tests
    python -m compileall -q src scripts tests

The workflow runs for merge requests and default-branch commits. The Python image uses a moving tag, not an immutable digest, and must be pinned in a separately reviewed change if the supply-chain policy requires that.

## Import the source into GitLab

GitLab's [official Repository by URL guide](https://docs.gitlab.com/user/import/third_party_systems/repo_by_url/) documents the following:

1. In GitLab select **Create new > New project/repository > Import project > Repository by URL**.
2. Use the public source URL https://github.com/Fadhilstat/PanganLens.git.
3. Choose an approved personal or group namespace and project name PanganLens if available. Never overwrite an unrelated project or select a namespace without permission.
4. Finish the import and inspect its status. Repository by URL imports Git history and files, but not GitHub issues or pull requests.
5. Compare GitLab's default branch to the verified GitHub main commit 9005b2a5fc5baa7b9e45a6cda552095b6b8b8349. If commits differ, inspect complete tree contents before reconciliation.
6. Verify the GitLab CI configuration and run or inspect an actual hosted pipeline. GitHub Actions success is not GitLab CI success.
7. A full import already includes the merged CI files. Open a GitLab MR only for a real subsequent change. Require a reviewed diff and successful CI before merging.

The connected GitLab actions available in this session do not include creating or importing a GitLab project. The first import must be completed through GitLab by an authorized user or an explicitly enabled project-create action.

## Boundaries

- No VPS, self-hosted runner, GCP authentication, or extra privileges.
- No automatic ingestion or publication, no scheduled refresh, and no secrets.
- No remote mirroring or force push to unrelated or diverged history.
- The PIHPS source-health probe does not prove production BigQuery readiness.
- GitHub Issue #48 remains the separate cloud activation checkpoint.
- Treat zero-cost operation as a goal with usage controls, not a guarantee.

## Rollback and next action

For a future GitLab-specific change, use a review branch, check its diff and CI, and merge only under the explicit approval gates. Reverting this isolated CI configuration does not require any warehouse or live-data rollback.

NEXT_ACTION: Create or import the authorized GitLab destination, then verify exact Git history or complete tree parity plus a real GitLab pipeline outcome.

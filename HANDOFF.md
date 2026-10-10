# HANDOFF

## Portfolio intent and source of truth

PanganLens is a public food-price analytics and data engineering portfolio, with static hosting but no fabricated market price feed. GitHub Fadhilstat/PanganLens is canonical, and the linked GitLab repository is fadhilrusydih/panganlens. The two repositories have different commit ancestry because GitLab was initially initialized from a content snapshot. Use file blob SHA parity to verify mirroring.

## Verified baseline (10 October 2026)

- GitHub main: 0d9f668ecd2a1c0a0152c554afe07a67f2b700a8.
- GitLab main: 4843ec71c3f20cac6b6cd76bffcae26995fd39c9.
- Previous release: GitHub PR #69, GitLab MR !4; GitLab pipeline #2932618806 SUCCESS.
- 155 of 155 source blob hashes matched at that release.
- GitLab project public but pages_access_level private. Previous GitHub Pages workflow blocked by disabled Pages configuration.
- Source price JSON is empty. GitHub Issue #48 separately gates cloud activation.

## Current cohesive release candidate

- Curated publish-state pointer is mandatory for nonempty exported prices. No pointer gives empty arrays; invalid pointer fails before publishing.
- Price SQL uses the active published observation date to avoid unreviewed later national values or historical province mixing.
- Website checks snapshot schema, arrays, run status, reviewed label and calendar date. Invalid or missing provenance is withheld, not displayed.
- scripts/check_public_snapshot.py is dependency-free and runs in both static Pages deployment pipelines.
- Expanded Python, Node, and CI contract tests enforce the same boundary.
- This checkpoint describes a candidate. Verify feature branches, merge commits, CI, and SHA parity live before saying RELEASED.

## Safe continuation

1. Review current branch HEADs and the exact changed diff. User granted APPROVE PUSH and APPROVE MERGE for this run, contingent on green CI.
2. Release one GitHub PR, verify quality tests + frontend tests + guarded PIHPS probe; merge only after success.
3. Mirror exact GitHub file contents to one GitLab MR, verify pipeline, merge, and verify main Pages deployment.
4. Compare all GitHub/GitLab file paths and blob SHA values; preserve separate ancestry.
5. Owner must change GitLab Pages visibility to Everyone with access under Settings > General > Visibility, project features, permissions; retrieve the actual website URL from Deploy > Pages and verify anonymous access.
6. No VPS, extra credentials, GCP activation, synthetic price data, or forced Git history rewrite.

NEXT_ACTION: Finish CI-gated public snapshot safeguards on both repositories and get the owner to make Pages public.

# HANDOFF

## Product and public launch boundary

PanganLens Indonesia is an auditable food-price analytics and data engineering portfolio. The website is a static preview, not a live price service. Its calculator uses only visitor-entered numbers. The included price JSON remains empty until separate BigQuery source/mapping/publication review under GitHub Issue #48.

## Source of truth before this candidate

- GitHub canonical repo: https://github.com/Fadhilstat/PanganLens
- GitLab target: https://gitlab.com/fadhilrusydih/panganlens
- Previous GitHub main SHA: 97e5fdd8f0478df6ca19a667945c90c6860c010d (PR #70).
- Previous GitLab main SHA: 1a7a18670eac7b32f8fbd831712604afe89a5cab (MR !5).
- GitLab main pipeline #2932757396: SUCCESS, including Pages deploy.
- Previous file-content parity: 157/157. Git commit histories differ due to original GitLab snapshot import.
- Pages domain provided by user: https://panganlens-679cd2.gitlab.io/
- GitLab project visibility: public. Pages access API still returned private. Anonymous access: NOT_VERIFIED in this runtime.
- GH Pages: optional, not yet enabled. No VPS required.

## Public portfolio release candidate

- Website has direct actions to calculation exercise and case study, better indication of preview status, footer links to code and CI.
- Meta tags include canonical, Open Graph, and social summary properties tied to the user-provided Pages domain.
- README and existing portfolio/data-delivery docs link to the real URL and clearly distinguish repository availability from anonymous website access.
- New scripts/check_public_site.py performs bounded anonymous HTTP checks of the deployed HTML, required assets and signed JSON payload; pytest covers its logic using network-free fixtures.
- GitLab's public_site_smoke job runs after deploy on main. It is intentionally allow_failure, so its warning is not proof of public availability and its failure does not block the separately validated code release.
- No claims of live PIHPS market data, production BigQuery refresh, synthetic portfolio statistics, or screenshot-tested responsiveness.

## Release process and gates

1. Confirm GitHub and GitLab main refs, branch, diff, and content hashes. No forced history rewrite.
2. User approved APPROVE PUSH and APPROVE MERGE for this turn; review CI before using the merge gate.
3. Merge a green GitHub PR. Transfer exact files to a GitLab review branch. Require green Python/frontend MR pipeline before merge.
4. Check GitLab main pipeline for Pages deploy and the separate public_site_smoke outcome.
5. Recheck GitHub and GitLab full path/blob SHA parity.
6. Only claim anonymous public reachability if the smoke passed or a true unauthenticated browser check succeeded. Even then, visual mobile screenshot QA remains separate.
7. Keep GitLab Pages access changes within the project owner's settings; no credential workarounds.

NEXT_ACTION: Inspect post-deploy smoke and make a truthful website portfolio release decision.

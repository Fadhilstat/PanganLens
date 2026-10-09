# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phases: Technical Implementation / Repository / Portfolio Preview
Status: PREVIEW_PAGES_DEPLOYED, PUBLIC_ACCESS_NOT_VERIFIED

## Verified release

- GitHub canonical source: https://github.com/Fadhilstat/PanganLens
- GitHub PR #67 merged at 1924451616d42949549cc86512455e1b56821d0a.
- GitHub full quality workflow #37974789018: SUCCESS, including Python, Node, and live PIHPS source probe.
- GitLab target: https://gitlab.com/fadhilrusydih/panganlens
- GitLab MR !2 merged at cd100cb30929d48703b15e5870a6b950ef78d79b.
- GitLab MR pipeline #2931785591: SUCCESS.
- GitLab main pipeline #2931787912: SUCCESS, including Python, Node, and static Pages deployment.
- File content matched 153/153 paths and Git blob SHA values after the merges; commit ancestry differs.
- Historical release SHAs are not permanent HEADs; fetch live refs before a new push.

## Public access and production boundaries

- GitLab project Pages access level: private. Public anonymous browsing: NOT_VERIFIED.
- GitHub Pages workflow #37974862397: FAIL during Configure Pages (HTTP 404, site not enabled in repository settings).
- Real public Pages URL: NOT_VERIFIED. Do not invent or advertise it.
- Production website/data/dashboard.json remains empty with null publish_state.
- GCP warehouse activation and real market prices: NOT_READY, separately tracked at GitHub Issue #48.
- GitLab Pages deployment is a portfolio preview, not proof of production market data.

## QA

- Core Python CI, lint, compile: PASS on both review workflows.
- Calculator Node unit tests (7), syntax checks: PASS.
- Full visual, keyboard and responsive browser QA on hosted URL: NOT_RUN.
- No VPS, GCP credential, source data fixture, ingestion schedule, or extra cloud privilege introduced.

## Final owner action

NOW: Set Pages access to Everyone with access under GitLab Settings > General > Visibility, project features, permissions, then verify the actual Pages URL from Deploy > Pages in a logged-out browser.

NEXT: Optionally configure GitHub Settings > Pages > Source: GitHub Actions and rerun the website dashboard workflow.

LATER: Finish Issue #48 activation and publish a first curated price snapshot.

OPTIONAL: Add browser E2E and accessibility testing after a reachable site URL exists.

NEXT_ACTION: Verify anonymous GitLab Pages access and its real URL, then add only that verified URL to README and portfolio profiles.

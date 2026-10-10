# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phases: 2 Technical Implementation, 3 Repository, 4 Go-to-market
Milestone: Portfolio landing, SEO and anonymous Pages release verification
Status: SOURCE_MERGED_AND_DEPLOYED, ANONYMOUS_PAGES_ACCESS_BLOCKED_HTTP_403

## Release results, verified

- GitHub canonical main at start of this checkpoint: fc550a128a15b68b3358b8e2dcf5cee8858b47c0 (PR #71 MERGED).
- GitHub quality run #38024816074: SUCCESS (pytest, Ruff, Python compile, Node, PIHPS source probe).
- GitLab main after MR !6 MERGED: 9767c0cd4a1cd198c7c5a2a8c7bedbb2ff60e7eb.
- GitLab main pipeline #2932828231: overall SUCCESS; python_quality, frontend_quality and deploy_portfolio_site SUCCESS.
- public_site_smoke in that pipeline: FAILED, job #17076922519. All 3 anonymous HTTPS GETs to https://panganlens-679cd2.gitlab.io/ returned HTTP 403 Forbidden.
- Post-merge parity check: 159/159 GitHub/GitLab source file Git blob SHAs match. Different Git commit histories remain expected.
- GitLab repository visibility: public. GitLab project Pages access level: private at last inspection despite owner reporting that it had been changed.
- The owner's URL is confirmed as the configured canonical/meta target in source. It is NOT confirmed anonymously available.
- Live browser visual, mobile screenshots, working calculator on deployed URL: NOT_RUN because hosted access is blocked.
- website/data/dashboard.json remains empty. No live validated PIHPS observations, no GCP activation, no VPS.

## Problems, solutions and opportunities

- BLOCKER: Anonymous visitor gets 403 at Pages root. Owner should set Pages access to Everyone with access under Settings > General > Visibility, project features, permissions, and save.
- The public-site smoke test is an explicit nonblocking signal to separate content quality from hosting authorization. Its FAILED status is evidence; an overall pipeline SUCCESS is not evidence of website reachability.
- Visual and keyboard QA can follow only after the actual website can be loaded without login. A direct public browser session is preferred.
- User approved PUSH and MERGE for the launch milestone. Continue using a reviewed branch, passing CI and a verified content diff for future changes.

NOW: Owner fixes GitLab Pages access and verifies https://panganlens-679cd2.gitlab.io/ in an incognito browser; rerun GitLab public_site_smoke job.
NEXT: When smoke PASS, update the README status and publish URL on LinkedIn/portfolio with clear preview labeling.
LATER: Activate real PIHPS data under GitHub Issue #48 with production quality gates.
OPTIONAL: Add screenshot/a11y regression testing for 360 px mobile, 768 px tablet and desktop.

NEXT_ACTION: Change Pages access from private to Everyone with access; then rerun the anonymous smoke job and only declare the website publicly ready if it passes.

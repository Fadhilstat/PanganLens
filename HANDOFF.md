# HANDOFF

## Goal and product scope

PanganLens is a portfolio of public food-price analytics, quality-gated data engineering, and a static user-input calculator. No unvalidated market observations are displayed. The production data snapshot is intentionally empty and cloud readiness is tracked separately under GitHub Issue #48. No VPS or new cloud credentials have been used.

## Last shipped source release

- GitHub Fadhilstat/PanganLens PR #71 merged; source SHA fc550a128a15b68b3358b8e2dcf5cee8858b47c0.
- GitHub Actions #38024816074: SUCCESS for Python quality, frontend and PIHPS probe.
- GitLab fadhilrusydih/panganlens MR !6 merged; main SHA 9767c0cd4a1cd198c7c5a2a8c7bedbb2ff60e7eb.
- GitLab main pipeline #2932828231: SUCCESS for Python quality, frontend and deploy_portfolio_site.
- File content SHA parity immediately after MR !6: 159/159 matched. Git history ancestry differs due to earlier snapshot import.
- Portfolio site HTML includes canonical/Open Graph/X summary pointing to https://panganlens-679cd2.gitlab.io/, useful links to calculator/case study and source repository, and mobile/keyboard CSS.

## Preview-first UX contract

- With the checked-in empty source JSON, the visitor should see the introduction, a data-unavailable notice, the user-input calculator, the case study, and the methodology. Price-only navigation, KPI cards, and unpopulated panels must remain hidden.
- Source-dependent content appears only for a successfully published snapshot with at least one usable national commodity row. Numeric and string commodity IDs must select the same commodity without hiding regional data.
- Node tests cover these pure checks; real browser layout and hosted navigation still need independent verification.
- No fake PIHPS observations or extra cloud activation were introduced.

## Confirmed launch blocker

- The owner supplied the GitLab unique Pages URL and said settings had been changed.
- GitLab API continued to report project public, pages_access_level private.
- GitLab job #17076922519 public_site_smoke ran without auth after Pages deployment and FAILED: root GET returned HTTP 403 three times.
- Thus public access is NOT VERIFIED and cannot be advertised yet. Overall CI green includes an explicitly allow_failure smoke job.
- An unauthenticated real-browser visual test was not performed. The HTTP check was blocked before any assets could be examined.
- GitLab connector cannot update project Pages access settings. Do not invent a workaround with tokens.

## Safe next steps

1. Owner checks GitLab project Settings > General > Visibility, project features, permissions and sets Pages access to Everyone with access, then saves. Ensure this is Pages visibility, not only repository visibility.
2. Open https://panganlens-679cd2.gitlab.io/ from a private/incognito browser without being logged into GitLab.
3. Retry job #17076922519 (or trigger a new main pipeline) using GitLab CI. A PASS must show real HTML, all assets and JSON in job trace.
4. Once anonymous smoke succeeds, update README status, verify desktop/mobile/keyboard UI, and publish the now-verified URL.
5. For any further code changes, re-fetch HEAD and CI, make reviewed PR/MR changes only, and retain exact content parity.

NEXT_ACTION: Fix GitLab Pages access control so the anonymous Pages check changes from HTTP 403 to PASS.

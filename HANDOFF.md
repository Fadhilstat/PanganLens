# HANDOFF

## Canonical project

- GitHub: https://github.com/Fadhilstat/PanganLens (source of truth).
- GitLab: https://gitlab.com/fadhilrusydih/panganlens (mirror, quality gates and older Pages fallback).
- Vercel new project: panganlens-portfolio, team ID team_EaaiSPOJWbSimQAe1AzNVd39.
- Production alias target: https://panganlens-portfolio.vercel.app/.
- Do not alter older Vercel panganlens-indonesia, which is linked to a different GitHub repository.

## Shipped before this run

- GitHub PR #73 and PR #74 merged, main SHA c212bab109ce5d5355eb7e1716fa7c091c5938ba.
- GitLab MR !8 and MR !9 merged, main SHA 67c209f1c6f04002025ff0e81306cab53a6b7ea3.
- Exact source parity before current milestone: 161/161 file blobs match.
- GitHub CI #38051263593 successful. GitLab main pipeline #2933444982 successful with GitLab Pages smoke warnings.
- Vercel manual production deployment dpl_DF3KR3knNBvgf4UkMgLhoVAvttQu READY.
- Anonymous Vercel HTTP has NOT been verified. No browser layout/keyboard test completed.

## This release contract

- Vercel must host static files rooted at website/. For REST inline deployments, upload paths prefixed website/ to match the project root.
- A test preview using root-level files failed with NOW_SANDBOX_WORKER_ROOTDIR_NOT_EXIST and did not replace production.
- Use anonymous HTTPS smoke with fixed production allowlist and data provenance guards. A build in READY state does not prove HTTP accessibility.
- Release candidate must pass GitHub Python and JavaScript tests, GitLab mirror tests, file parity and Vercel public smoke.
- Keep production price snapshot empty until separate reviewed PIHPS source and warehouse publication approval.
- Calculator accepts only visitor-entered amounts. Do not invent live prices or usage metrics.
- Vercel GitHub integration is missing for canonical repo; owner must install it for automatic deployment.
- All source changes follow reviewed feature branch, PR/MR and verified CI before merge.

## QA and safety boundaries

- Preserve source snapshot checker, quality gates, data source provenance, accessibility states and no credentials in browser.
- Actual responsive visual (360px, 768px, desktop), browser keyboard navigation and form submission verification are NOT_RUN until executed.
- The blocked GitLab Pages domain must not be promoted as public.
- No VPS, cloud keys or paid infrastructure requested.

NEXT_ACTION: Verify external anonymous Vercel smoke and exact production source revision. If PASS, carry out real browser QA before posting on LinkedIn.

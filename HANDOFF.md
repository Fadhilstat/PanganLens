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
- Anonymous Vercel HTTP was verified by GitLab MR !10 job #17080370537 (all assets and preview snapshot PASS). GitHub Chrome browser QA #114213562658 passed at 360/768/1440 px, including calculator and keyboard focus.

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
- GitHub browser-quality completed PASS in workflow #38052253101; retained screenshot artifact #11669544645 enables optional manual aesthetics review. Automated browser functional QA and unauthenticated public HTTP smoke are both verified.
- The blocked GitLab Pages domain must not be promoted as public.
- No VPS, cloud keys or paid infrastructure requested.

NEXT_ACTION: Owner connects Vercel GitHub integration to Fadhilstat/PanganLens for automatic main deployment. The public portfolio preview is live and independently verified; activation of price data requires separate approval.

## Latest public release checkpoint (verified)

- GitHub PR #75 merged, main SHA 0234893d6db6ac09aa5d673eb983b0053bd7c58c.
- GitLab MR !10 merged, main SHA b39d1f835202cfb1a2b72020fee4278770d2d11e.
- 162/162 source blobs match across canonical and mirror repositories.
- Vercel production deployment dpl_AMPHmiCdttsw8xGaYSGKzttiBRdV READY at https://panganlens-portfolio.vercel.app/.
- GitLab main pipeline #2933465351 public smoke job #17080390567 PASS after this deployment.
- GitHub Actions #38052358434 SUCCESS (Python, frontend, PIHPS source probe, browser Chrome).
- Browser QA covers 360px, 768px and 1440px, calculator math/reset, keyboard skip focus and no horizontal overflow. Screenshots in artifact #11669871395.
- This checkpoint changes docs only and does not require another website/ redeployment.
- Public sharing is truthful only as a portfolio preview, with the checked-in JSON empty and PIHPS production activation gated.


## Data research milestone continuation

- `src/panganlens/ingestion/research_sample.py` implements an isolated,
  read-only source-audit and CSV export boundary.
- `scripts/export_pihps_research_sample.py` uses live PIHPS GET-only captures.
- `tests/test_research_sample.py` checks source integrity, reference identities,
  duplicate keys, missing prices, stale review flags and spreadsheet safety.
- GitHub PR/manual `live-pihps-probe` exports a short-lived source artifact;
  scheduled probe remains source-schema-only.
- Research output is not allowed inside website/ and must never be confused with
  BigQuery curated price rows or verified production readiness.
- No GCP bootstrap/apply, credentials, scheduling, mapping approval or production
  snapshot edits are authorized by this change.

NEXT_ACTION: Inspect CI source artifact and validate the raw-to-reviewed mapping
plan, then continue Issue #48 activation through explicit operator-controlled gates.

- Live PIHPS source research evidence was captured in GitHub Actions:
  27 source price points, 9 observation dates, 3 original row levels,
  0 missing price cells, latest 2026-10-09. No warehouse publication.
- The province filter is not each returned row's geographic identity.
  Source rows in the sample included all-provinces, DKI and Jakarta Pusat.
  CSV fields now use request_province_filter_id/name to prevent that
  analytical join error before reviewed canonical mapping.

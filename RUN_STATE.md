# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phases: 2 Technical Implementation, 3 Repository, 4 Go-to-market
Milestone: Verified public Vercel launch, source parity and frontend QA
Status: CODE_MERGED, VERCEL_BUILD_READY, ANONYMOUS_HTTP_UNVERIFIED

## Verified source and quality evidence

- GitHub main after PR #74 MERGED: c212bab109ce5d5355eb7e1716fa7c091c5938ba.
- GitHub editorial PR #74 CI run #38051263593: SUCCESS for Python tests, frontend Node and PIHPS source probe.
- GitLab main after MR !9 MERGED: 67c209f1c6f04002025ff0e81306cab53a6b7ea3.
- GitLab main pipeline #2933444982: SUCCESS with warnings. GitLab Pages public smoke still targets the locked old host and is nonblocking.
- Post merge 161/161 source Git blobs matched across GitHub and GitLab.
- Vercel personal Hobby team: fadhil-9768s-projects.
- Vercel new project: panganlens-portfolio, ID prj_Fhc0Q04IUEIPrwwEW1xaF7qTDKEj.
- Initial manual production deployment dpl_DF3KR3knNBvgf4UkMgLhoVAvttQu: READY with aliases panganlens-portfolio.vercel.app and panganlens-portfolio-fadhil-9768s-projects.vercel.app.
- Vercel production project has no SSO/password protection in connector metadata, but independent anonymous HTTP availability is not verified.
- A test preview using root-level source files errored NOW_SANDBOX_WORKER_ROOTDIR_NOT_EXIST; production upload must preserve website/ paths for the configured root.
- Vercel GitHub integration for canonical Fadhilstat/PanganLens was not installed when linking was attempted. Owner action is needed for auto-deploy.

## Product and data boundaries

- CSS-based green editorial redesign is merged. No Dribbble art assets were copied.
- The interactive user-input calculator remains available and tested. No browser production visual audit was completed.
- Source-dependent KPI panels remain hidden until verified price observations exist.
- website/data/dashboard.json is intentionally empty. No validated PIHPS production snapshot, VPS, cloud credential or GCP activation was added.

## This milestone

- Update anonymous smoke verification to the actual Vercel production domain with an explicit same-host allowlist.
- Reject wrong or unreviewed layout, missing assets, invalid snapshot and authentication redirects.
- Run the public HTTP smoke from GitLab merge request and main CI (nonblocking until auto-deploy).
- Add regression tests and no-store caching for dashboard.json.
- Redeploy exact merged source to Vercel and inspect both CI and public accessibility before claiming launch-ready.

## Problems, solutions, opportunities

- HIGH: Anonymous Vercel HTTP access has not yet passed an external smoke test. Deploy READY alone is insufficient.
- MEDIUM: No GitHub to Vercel auto-deploy integration; manual source upload needs care with the project root and revision.
- MEDIUM: Visual desktop/mobile/browser audit remains NOT_RUN.
- LOW: GitLab Pages still requires login and remains a documented fallback failure.
- Opportunity: a clear, reproducible public portfolio launch check demonstrates engineering trust and release discipline.

NOW: GitLab Vercel smoke, exact source redeploy and anonymous availability check.
NEXT: Browser responsive and calculator QA for 360px, 768px and desktop.
LATER: Reviewed PIHPS production data under GitHub Issue #48.
OPTIONAL: Case study visuals and LinkedIn publishing pack.

NEXT_ACTION: Verify new Vercel anonymous smoke job and redeploy the exact passing main revision, then decide launch status from observed results.

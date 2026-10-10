# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phases: 2 Technical Implementation, 3 Repository, 4 Go-to-market
Milestone: Verified public Vercel launch, source parity and frontend QA
Status: PUBLIC_PORTFOLIO_PREVIEW_READY, VERCEL_DEPLOYED_AND_ANONYMOUS_SMOKE_PASSED

## Verified source and quality evidence

- GitHub main after PR #74 MERGED: c212bab109ce5d5355eb7e1716fa7c091c5938ba.
- GitHub editorial PR #74 CI run #38051263593: SUCCESS for Python tests, frontend Node and PIHPS source probe.
- GitLab main after MR !9 MERGED: 67c209f1c6f04002025ff0e81306cab53a6b7ea3.
- GitLab main pipeline #2933444982: SUCCESS with warnings. GitLab Pages public smoke still targets the locked old host and is nonblocking.
- Post merge 161/161 source Git blobs matched across GitHub and GitLab.
- Vercel personal Hobby team: fadhil-9768s-projects.
- Vercel new project: panganlens-portfolio, ID prj_Fhc0Q04IUEIPrwwEW1xaF7qTDKEj.
- Initial manual production deployment dpl_DF3KR3knNBvgf4UkMgLhoVAvttQu: READY with aliases panganlens-portfolio.vercel.app and panganlens-portfolio-fadhil-9768s-projects.vercel.app.
- Vercel production access independently VERIFIED: GitLab MR !10 public_site_smoke job #17080370537 returned PUBLIC_VERCEL_SMOKE_PASS (all assets, canonical URL and empty reviewed JSON).
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
- Add headless Chrome QA at 360px, 768px and 1440px with calculator, overflow, focus and error assertions; require passing GitHub CI.
- Redeploy exact merged source to Vercel and inspect both CI and public accessibility before claiming launch-ready.

## Problems, solutions, opportunities

- RESOLVED: Anonymous Vercel HTTP smoke PASS from public GitLab runner, no login or credentials.
- MEDIUM: No GitHub to Vercel auto-deploy integration; manual source upload needs care with the project root and revision.
- RESOLVED FOR FUNCTIONAL QA: GitHub Actions browser-quality job #114213562658 passed responsive Chrome tests at 360/768/1440 px, calculator, keyboard skip-link visibility, empty state, no overflow and zero page errors. Screenshot artifact #11669544645 is available for manual aesthetic review.
- LOW: GitLab Pages still requires login and remains a documented fallback failure.
- Opportunity: a clear, reproducible public portfolio launch check demonstrates engineering trust and release discipline.

NOW: Public portfolio preview is available at https://panganlens-portfolio.vercel.app/ and has passed post-merge smoke.
NEXT: Owner enables GitHub-Vercel repository integration and optionally reviews retained Chrome screenshots before the LinkedIn announcement.
LATER: Reviewed PIHPS production data under GitHub Issue #48.
OPTIONAL: Case study visuals and LinkedIn publishing pack.

NEXT_ACTION: Owner authorizes the Vercel GitHub integration for Fadhilstat/PanganLens so future main pushes deploy automatically; keep the public snapshot empty until PIHPS publication is approved.

## Release candidate QA evidence (2026-10-10)

- GitHub PR #75 browser and full quality workflow run #38052253101: SUCCESS.
- Chrome browser-quality job #114213562658: PASS at width 360, 768 and 1440 px, real calculator arithmetic 10%/20%, reset, focus, no overflow and no JavaScript page errors.
- Screenshot artifact 11669544645 exists for manual visual review.
- GitLab MR !10 pipeline #2933461706: Python and Node checks passed. Vercel smoke job #17080370537: PASS with 13291 HTML bytes, 5 static assets and schema-1 empty preview snapshot.
- This verifies the existing production Vercel deployment, not the upcoming source changes to JSON caching and CI; redeploy exact main and verify again before declaring current revision live.

## Final production release verified

- GitHub PR #75 MERGED to main commit 0234893d6db6ac09aa5d673eb983b0053bd7c58c.
- GitLab MR !10 MERGED to main commit b39d1f835202cfb1a2b72020fee4278770d2d11e.
- Post-merge GitHub/GitLab blob parity: 162/162 matched.
- Vercel production deployment dpl_AMPHmiCdttsw8xGaYSGKzttiBRdV: READY; GitHub main SHA 0234893d6db6ac09aa5d673eb983b0053bd7c58c.
- Latest anonymous HTTPS production check after deployment: GitLab main pipeline #2933465351, job #17080390567, PUBLIC_VERCEL_SMOKE_PASS.
- Latest GitHub PR quality run #38052358434: SUCCESS including Chrome browser QA on 360/768/1440 px and screenshot artifact #11669871395.
- Public preview is appropriate to share as a transparent engineering portfolio case study, not as live PIHPS price coverage.
- GitLab Pages still returns 403 but is no longer the primary publication URL. Vercel GitHub integration is still manual setup.
- This final release-status checkpoint only edits documentation; website/ hashes and production content remain unchanged.


## Data milestone: narrow PIHPS source research candidate

- New read-only research exporter for one verified source commodity/province and a bounded historical window.
- Export includes original price observations in a temporary CSV, plus JSON with raw capture
  fingerprint, count of valid and missing cells, observation date, and explicit review flags.
- Deterministic schema, reference membership, positive-price parsing, hash integrity
  and repeated-key checks block unsafe captures. Output is never a curated snapshot.
- GitHub PR and manual quality runs can store a short-lived source review artifact;
  scheduled source probe remains schema-only and never exports price rows.
- This change intentionally does not select a GCP project, run BigQuery SQL, activate
  ingestion scheduling, approve mappings, or alter website/data/dashboard.json.

NOW: Validate real source research capture through CI and inspect artifact metadata.
NEXT: Review source names against canonical commodity/province registry; then continue
Issue #48 cloud activation only when the operator supplies reviewed GCP/WIF evidence.
LATER: Populate curated marts with verified observations and publish pointer.
OPTIONAL: Multi-region data quality report after one single-scope capture is reviewed.

NEXT_ACTION: Run source research CI against live PIHPS, review CSV and SHA evidence,
then decide mappings before any production price publication.

- First live research sample CI artifact #11670741984 (2026-10-10) contained
  27 price points from 3 source row levels across 9 observed dates (latest
  2026-10-09), 0 missing cells. Research-only, publish_eligible=false.
- Review found that a province-filtered source response includes rows for
  "Semua Provinsi", "DKI Jakarta", and "Kota Jakarta Pusat"; the exporter now
  names the request filter separately from each row's source level/name.

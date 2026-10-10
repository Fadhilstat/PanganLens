# HANDOFF

## Product and purpose

PanganLens Indonesia is a food-price data engineering and analytics portfolio. It combines guarded PIHPS ingestion, reviewed mapping, BigQuery warehouse contracts, curated mart publication rules, and a static dashboard. Do not claim live market prices until source, mapping, quality and publish-state gates pass. The public snapshot is currently empty. The separate browser calculator uses visitor-provided numbers only.

## Verified baseline at 10 October 2026

- GitHub canonical: https://github.com/Fadhilstat/PanganLens
- GitLab project: https://gitlab.com/fadhilrusydih/panganlens
- GitHub pre-candidate main SHA 761b6eebc9dfc848785e6d0e326ef06d06d9d068.
- GitLab pre-candidate main SHA 590bada6cf6d270bc126bf4de5681967c8bf8de1.
- Prior 153 Git blobs matched across both platforms, but commit histories differ from GitLab snapshot import.
- GitLab prior main pipeline 2931802651: SUCCESS with static Pages job.
- GitLab pages_access_level: private, so an anonymous public website is not yet verified.
- GitHub Pages not yet enabled in repo settings, prior deployment workflow #37974862397 returned Configure Pages 404.
- Cloud readiness and price publication gated separately by GitHub issue #48.

## Current candidate: fail-closed analytical selectors

1. In website/dashboard_metrics.js choose only positive-change rows for top rise and negative-change rows for top fall. Missing or invalid prices and percentages are not valid observations.
2. Region ranking excludes rows without a finite gap or positive price; actual numeric zero gap remains a valid equal-to-average value.
3. website/app.js uses these selectors, preserves explicit empty states and prevents trends built from nonpositive prices.
4. index.html loads dashboard_metrics.js before app.js. GitHub/GitLab CI test both JavaScript modules, all Node tests and Python contracts.
5. Local 9/9 tests passed on the two exact metric files whose blob SHA was compared with candidate tree. Entire repository CI is pending until a branch push.

## Safe continuation and blockers

- Review exact diff, create one GH PR, require green Python, Node, live source probe before merging.
- Transfer only reviewed changes to a new GitLab feature branch, require successful MR pipeline, then merge and compare full tree hashes.
- The owner must enable public Pages by selecting Everyone with access under GitLab Settings > General > Visibility, project features, permissions, then fetch the actual Pages URL from Deploy > Pages and verify anonymous access.
- Optionally enable GitHub Pages with Source: GitHub Actions under repo Settings > Pages; do not introduce additional PATs or tokens.
- No VPS, no GCP role, no secret, no new production snapshot or scheduled data refresh.

NEXT_ACTION: Finish CI-gated analytical semantics release on both platforms, then make Pages public via the owner setting and verify the deployed URL.

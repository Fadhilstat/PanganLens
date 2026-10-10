# PanganLens Indonesia

**An auditable food-price analytics project built around public Indonesian data.**

PanganLens explores a practical question: *how can a food-price dashboard make trends understandable without quietly publishing unverified numbers?* It combines guarded source ingestion, a normalized BigQuery model, mapping review, quality gates, and a lightweight public-facing website.

**Portfolio hosting:** the latest manually deployed production release at [Vercel](https://panganlens-portfolio.vercel.app/) reached `READY` (deployment `dpl_AMPHmiCdttsw8xGaYSGKzttiBRdV`, based on canonical main commit `0234893d6db6ac09aa5d673eb983b0053bd7c58c`). Anonymous production access was verified on 10 October 2026 by GitLab main job #17080390567, after the final production redeploy: `PUBLIC_VERCEL_SMOKE_PASS`. The editorial portfolio preview, CSS, JavaScript and empty validated JSON all loaded without credentials. GitLab Pages previously returned HTTP 403 and is not the promoted public host. GitLab remains the code and CI mirror. The Vercel GitHub integration for this repository must still be authorized by the owner to enable automatic deployments.

**Data status (10 October 2026):** this is a data engineering portfolio preview, **not a live PIHPS price dashboard**. The checked-in production snapshot is empty; visitors can use the calculator with their own numbers.

**Preview-first visitor experience:** source-dependent KPI cards, national/province sections, and their navigation links stay hidden when a verified snapshot has no usable national price record. The calculator, case study, and methodology stay accessible. Commodity selections normalize numeric warehouse IDs and string browser option values. This does not bypass any publication gate.

[Vercel production URL, verify public access](https://panganlens-portfolio.vercel.app/) | [Explore the website source](website/) | [Read the case study](docs/portfolio_case_study.md) | [Inspect quality gates](docs/data_safety_contract.md) | [See cloud activation criteria](https://github.com/Fadhilstat/PanganLens/issues/48)

## Why this project exists

Raw price feeds can be incomplete, revised, duplicated, or mapped inconsistently between commodities and provinces. A polished chart cannot make a bad data contract trustworthy. The core design principle here is to **stop invalid records before they become public statistics**, while keeping the calculation and publication logic explainable.

**Intended users:** people comparing Indonesian food-price movements, policy researchers, journalists, and analysts. **Portfolio audience:** recruiters and engineering reviewers who want to inspect working source code, reproducible checks, security boundaries, and deliberate tradeoffs.

## What visitors can use now

- **Guided dashboard:** national commodity and provincial comparison components, clearly showing unavailable states until a valid curated snapshot exists.
- **Interactive price exercise:** visitors enter four positive rupiah amounts, then see the percentage change and deviation from a provincial average. Calculations run locally, are tested, and never claim to be PIHPS observations.
- **Transparent case study:** architecture, source safeguards, important decisions, current blockers, and exact evidence for testing.

The interactive exercise uses the following formulas:

~~~text
price_change_pct = (current_price - previous_price) / previous_price
province_gap_pct = (region_price - province_average) / province_average
~~~

Both denominators must be positive. The browser checks for empty, zero, negative, malformed, and non-finite input. Display formatting is separate from numeric calculation.

## Actual architecture

~~~text
PIHPS Bank Indonesia website interface (guarded, not a stable public API)
    |
    v
Transport and schema checks + source fingerprint
    |
    v
Parse and validate + exact duplicates and conflicting values
    |
    v
Canonical commodity / province mapping review
    |
    v
BigQuery raw -> staging -> normalized core (3NF)
    |
    v
Pre-promotion and post-load quality assertions
    |
    v
Curated mart + publish-state checks
    |
    +--> Looker Studio (proposed, curated views only)
    |
    +--> Verified JSON snapshot -> static website (production data pending)
~~~

The source client refuses unreviewed transport/schema changes. Production bootstrap has its own plan-hash and least-privilege authorization boundaries. Data publication does not follow from a successful source request alone.

## Technology and implementation

| Layer | Technology / approach |
| --- | --- |
| Ingestion | Python, requests, guarded PIHPS interface and parser |
| Modeling | BigQuery SQL, normalized 3NF, curated semantic views |
| Data quality | Mapping review, duplicate/conflict quarantine, publish-state gate |
| Frontend | Plain HTML, CSS, JavaScript; no framework or browser credentials |
| Test suite | pytest, Ruff, Python compile, Node built-in test runner |
| Delivery | GitHub Actions and GitLab CI; static Pages deployments |
| Secrets | No key files or cloud credentials in the frontend or source tree |

This is intentionally a small static frontend, not an always-on server. A live data pipeline requires separate cloud setup and quality approvals described in the existing docs.

## Responsive browser acceptance test

GitHub Actions runs a real headless Chrome browser check at 360px, 768px and 1440px.
It checks empty-state visibility, horizontal overflow, keyboard focus, calculator
arithmetic, reset behavior and uncaught JavaScript errors. Screenshots are kept as
short-lived CI artifacts. Locally, with Chrome available, run:

~~~bash
npm install --no-save --no-package-lock --ignore-scripts playwright-core@1.61.1
node --test tests/browser_portfolio.test.cjs
~~~

## Reproduce checks

Requires Python 3.11+; for the browser calculation tests, Node 22+.

~~~bash
python -m pip install -c constraints/ci.txt -e ".[dev]"
pytest -q
ruff check src scripts tests
python -m compileall -q src scripts tests
node --check website/app.js
node --check website/dashboard_metrics.js
node --check website/price_playground.js
node --test tests/dashboard_metrics.test.cjs tests/price_playground.test.cjs
python scripts/check_public_snapshot.py website/data/dashboard.json
~~~

To view the static site locally, run:

~~~bash
python -m http.server 8000 --directory website
~~~

Then open http://localhost:8000. There is no authentication, running database, background service, VPS, or secret needed for the preview.

## Repository navigation

| Path | Purpose |
| --- | --- |
| [website/](website/) | Accessible dashboard, price calculation exercise, empty/error states |
| [src/panganlens/](src/panganlens/) | Domain models, pipeline code, mapping, warehouse and readiness |
| [sql/](sql/) | Raw/staging/core structures, promotion gates, semantic views |
| [tests/](tests/) | Data contracts, pipeline controls, security, frontend tests |
| [docs/portfolio_case_study.md](docs/portfolio_case_study.md) | Problem, decisions, QA, remaining risks |
| [docs/dashboard_delivery.md](docs/dashboard_delivery.md) | Static hosting, snapshot policy, release conditions |
| [RUN_STATE.md](RUN_STATE.md) | Most recent execution checkpoint |
| [HANDOFF.md](HANDOFF.md) | Safe continuation instructions |

## Interpretation safeguards

A percentage is only useful when its sign, denominator and missing-data behavior are correct:

- **Kenaikan terbesar:** choose the highest valid **positive** daily change. When every valid commodity falls or stays flat, show no rise.
- **Penurunan terbesar:** choose the lowest valid **negative** daily change. When every valid commodity rises or stays flat, show no fall.
- **Provincial comparison:** a missing price gap is unknown, not zero. Rows lacking a valid gap or positive price are excluded from ranking. An actual numeric zero gap is retained as an equal-to-average observation.
- **Price trend:** previous and current prices must both be positive before drawing a comparison.

The business logic is isolated in [website/dashboard_metrics.js](website/dashboard_metrics.js), with 9 sign, missingness, input and ranking tests in [tests/dashboard_metrics.test.cjs](tests/dashboard_metrics.test.cjs). The interactive calculator is intentionally separate from the publication snapshot and continues to use only visitor-provided input.

## Fail-closed snapshot publication

A source request or a BigQuery query succeeding does not automatically approve a public price. The exporter now checks the curated `vw_looker_publish_state` pointer first. With no active publish state, it exports **zero prices**. A state must reference a `SUCCESS` run, a valid observation date, and one of the reviewed freshness labels before price queries are allowed.

National prices are bounded by the active published observation date; province comparisons use that exact date. Before either Pages deployment, `scripts/check_public_snapshot.py` rejects malformed JSON, unsupported schema versions, and any priced payload lacking a successful publication pointer. The browser independently refuses to display data without valid provenance. The checked-in preview remains empty, not synthetic.

Run the dependency-free release check locally:

~~~bash
python scripts/check_public_snapshot.py website/data/dashboard.json
~~~

## Evidence and honest limitations

**Implemented:** guarded source interactions, numeric parsing, duplicate handling, review gates, BigQuery schemas, snapshot exporter, safety tests, and a public-site UI. CI checks are configured in GitHub and GitLab.

**Not claimed:** live synchronized prices, production data completeness, a successful production BigQuery refresh, cost-free unlimited cloud usage, or an operational Looker Studio link. These require separately verified evidence. The existing [cloud activation checklist](https://github.com/Fadhilstat/PanganLens/issues/48) must remain intact.

The website remains safe to publish as a **portfolio preview**: no unsupported market numbers are displayed. GitLab and GitHub have matching file contents at the last checked baseline, but not identical commit histories. Future releases should compare file blob hashes and run both platforms' CI before updating each main branch.

## Roadmap

**NOW:** Verify anonymous GitLab Pages access via the hosted smoke check, then share the preview URL with an accurate no-live-data label. Optional GitHub Pages hosting remains separate.

**NEXT:** Obtain reviewed mappings, activate BigQuery with short-lived identity, and publish the first validated price snapshot.

**LATER:** Connect curated marts to Looker Studio and add longer price time-series with labeled observation gaps.

**OPTIONAL:** Expand accessibility and user research, and build a traceable release monitor.

## Author

Personal data engineering and analytics portfolio project. [LinkedIn](https://www.linkedin.com/in/fadhilrusydi31/) | [GitHub](https://github.com/Fadhilstat) | [GitLab](https://gitlab.com/fadhilrusydih).


## Verified release evidence

- [GitHub PR #67](https://github.com/Fadhilstat/PanganLens/pull/67) merged with [full CI success](https://github.com/Fadhilstat/PanganLens/actions/runs/37974789018).
- [GitLab MR !2](https://gitlab.com/fadhilrusydih/panganlens/-/merge_requests/2) merged with [successful MR CI](https://gitlab.com/fadhilrusydih/panganlens/-/pipelines/2931785591).
- [GitLab main CI and Pages deployment](https://gitlab.com/fadhilrusydih/panganlens/-/pipelines/2931787912): SUCCESS. Immediately after merging, all 153 file blob SHA values matched across the two repositories.
- [GitHub Pages deployment](https://github.com/Fadhilstat/PanganLens/actions/runs/37974862397): FAIL at Configure Pages with HTTP 404 because repository Pages had not been enabled. This is a hosting settings issue.
- GitLab Pages access control reported private. Do not treat successful artifact deployment as verified public reachability.

Owner steps: set GitLab **Settings > General > Visibility, project features, permissions > Pages** to **Everyone with access** and find the actual URL under **Deploy > Pages**. Optional GitHub site: set **Settings > Pages > Build and deployment > Source: GitHub Actions**, then rerun the existing website workflow. No VPS is needed.


## Latest release evidence and access blocker (10 October 2026)

- GitHub PR [#71](https://github.com/Fadhilstat/PanganLens/pull/71) merged at `fc550a128a15b68b3358b8e2dcf5cee8858b47c0`; Actions [#38024816074](https://github.com/Fadhilstat/PanganLens/actions/runs/38024816074) passed Python, JavaScript, Ruff, and PIHPS probe.
- GitLab MR [!6](https://gitlab.com/fadhilrusydih/panganlens/-/merge_requests/6) merged at `9767c0cd4a1cd198c7c5a2a8c7bedbb2ff60e7eb`; [main pipeline #2932828231](https://gitlab.com/fadhilrusydih/panganlens/-/pipelines/2932828231) passed Python, frontend, and Pages deploy.
- Exact GitHub/GitLab repository file-content parity: **159 of 159 blob hashes matched**.
- The nonblocking [public site smoke job #17076922519](https://gitlab.com/fadhilrusydih/panganlens/-/jobs/17076922519) **FAILED**, returning HTTP 403 Forbidden on all three unauthenticated attempts to the website root. The pipeline's green status does not override this separate failed check.
- GitLab API still reports `pages_access_level: private`, although the repository is public and the owner attempted to change the visibility. Only the project owner can fix the Pages access setting with available tools.

**Current acceptance:** SOURCE_READY and STATIC_DEPLOYED, but ANONYMOUS_ACCESS_BLOCKED and BROWSER_VISUAL_QA_NOT_RUN. Production PIHPS market data remains unpublished and Issue #48 controls cloud activation.

## Public website checks

The repository owner supplied the GitLab Pages URL: [https://panganlens-679cd2.gitlab.io/](https://panganlens-679cd2.gitlab.io/). The static site includes canonical and social-sharing metadata for that address, a direct entry point to the user-input calculator, and links to source code. No cover image, testimonials, live price statistics, or unverified analytics have been invented.

After GitLab Pages publishes from `main`, the `public_site_smoke` job requests the website **without authentication**. It checks the actual HTML, social metadata, CSS, JavaScript assets, and dashboard JSON. This job is deliberately nonblocking because Pages propagation and access settings are independent from code tests; a failed smoke job still means public reachability is **NOT_VERIFIED**. Its outcome must be inspected before posting the link publicly.

To repeat this external check from an internet-connected machine:

~~~bash
python scripts/check_public_site.py --url https://panganlens-679cd2.gitlab.io/ --attempts 1
~~~

This is a HTTP/content-level smoke test, not a desktop/mobile screenshot audit. The interface has keyboard, focus, reduced-motion, mobile CSS, and contract tests, while real-browser visual testing remains an independent review step.


## Current source-data research workflow

The production BigQuery snapshot is still empty because canonical mappings, write IAM
and the active publication pointer have not been independently approved under Issue #48.
The website must not show unreviewed PIHPS values.

A new **zero-cloud-write research capture** retrieves just one original PIHPS commodity
and province over an 11-day calendar window, validates the two source references and
price grid schema, parses positive integer rupiah prices, counts missing price cells,
rejects duplicate source keys, verifies raw SHA-256 evidence, and preserves source IDs
without asserting canonical entity mappings. A stale observation is flagged for review.

Use this command on a networked workstation:

~~~bash
python scripts/export_pihps_research_sample.py --output-dir /tmp/pihps-research
~~~

The default scope is PIHPS source ID `com_3` (commodity), province ID `13`,
and the eleven calendar days ending on the previous business day. These IDs are
validated against **fresh reference responses** rather than mapped by name. It
creates `source_audit.json` and `unreviewed_source_prices.csv`; all exported
observations carry `UNREVIEWED_SOURCE_SAMPLE`, and no files are written to `website/`.
A GitHub pull request or manual quality workflow run produces a short-lived
`pihps-unreviewed-research-sample` artifact. The scheduled source-health probe
does not export any price data. No BigQuery query or cloud credential is needed.

This is a review aid for the mapping and quality pipeline, not a way to bypass
the independent BigQuery readiness, provenance, and publish-state requirements.

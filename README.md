# PanganLens Indonesia

**An auditable food-price analytics project built around public Indonesian data.**

PanganLens explores a practical question: *how can a food-price dashboard make trends understandable without quietly publishing unverified numbers?* It combines guarded source ingestion, a normalized BigQuery model, mapping review, quality gates, and a lightweight public-facing website.

**Portfolio status (10 October 2026):** the GitHub and GitLab code releases passed CI, and GitLab's static Pages deployment job succeeded. However, **anonymous Pages access is not yet verified**, because the project's Pages visibility is private. GitHub Pages still needs repository settings enabled. Verified live food prices are not published; the checked-in snapshot is deliberately empty. The calculator uses visitor-provided input only.

[Explore the website source](website/) | [Read the case study](docs/portfolio_case_study.md) | [Inspect quality gates](docs/data_safety_contract.md) | [See cloud activation criteria](https://github.com/Fadhilstat/PanganLens/issues/48)

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

## Reproduce checks

Requires Python 3.11+; for the browser calculation tests, Node 22+.

~~~bash
python -m pip install -c constraints/ci.txt -e ".[dev]"
pytest -q
ruff check src scripts tests
python -m compileall -q src scripts tests
node --check website/app.js
node --check website/price_playground.js
node --test tests/price_playground.test.cjs
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

## Evidence and honest limitations

**Implemented:** guarded source interactions, numeric parsing, duplicate handling, review gates, BigQuery schemas, snapshot exporter, safety tests, and a public-site UI. CI checks are configured in GitHub and GitLab.

**Not claimed:** live synchronized prices, production data completeness, a successful production BigQuery refresh, cost-free unlimited cloud usage, or an operational Looker Studio link. These require separately verified evidence. The existing [cloud activation checklist](https://github.com/Fadhilstat/PanganLens/issues/48) must remain intact.

The website remains safe to publish as a **portfolio preview**: no unsupported market numbers are displayed. GitLab and GitHub have matching file contents at the last checked baseline, but not identical commit histories. Future releases should compare file blob hashes and run both platforms' CI before updating each main branch.

## Roadmap

**NOW:** Make the deployed GitLab Pages site publicly accessible, verify its URL without signing in, and optionally enable GitHub Pages.

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

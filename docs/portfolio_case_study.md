# PanganLens: Data Engineering and Analytics Case Study

## Problem

Food-price data is useful only if observers can identify what was measured, when it was observed, and whether it was published through a valid transformation. An apparently precise percentage can be wrong if source schemas shift, commodity mappings conflict, observations are revised, or comparisons mix channels and units.

## Product hypothesis

A trustworthy public-facing price product should make three tasks straightforward: understand how a value was obtained, compare only equivalent observations, and recognize when data is not ready to publish.

For a reviewer, the project should also make tests and design choices inspectable.

## Scope and architecture

The guarded source is PIHPS Bank Indonesia's public website interface. It is not advertised here as a stable official API. The Python client checks allowed hosts, response types, payload limits, source fingerprints, dynamic dates, and validation constraints. Approved mapping rules align commodities and regions. Duplicates are classified, conflicts quarantined, and revisions tracked.

The SQL layer separates source/raw capture, staging, operational records, normalized core entities, and curated mart views. Promotion is blocked until pre- and post-load assertions hold. Looker Studio must only consume curated views. The JSON exporter has a query-bytes ceiling and serializes exact BigQuery decimals as strings before browser formatting.

Relevant code and tests:

- Source contract: [src/panganlens/ingestion/pihps_interface.py](../src/panganlens/ingestion/pihps_interface.py)
- Mapping review: [src/panganlens/ingestion/mapping_operator.py](../src/panganlens/ingestion/mapping_operator.py)
- Promotion SQL: [sql/010_promote_staging_to_core.sql](../sql/010_promote_staging_to_core.sql)
- Dashboard exporter: [src/panganlens/dashboard_snapshot.py](../src/panganlens/dashboard_snapshot.py)
- Price exercise: [website/price_playground.js](../website/price_playground.js)
- Test suite: [tests/](../tests/)

## Three product decisions

1. **A failed publish-state gate does not silently turn into a misleading chart.** The checked-in production snapshot contains no prices and a null publish state. Empty and error states are part of the interface contract.
2. **The public website does not directly query BigQuery or carry cloud credentials.** It reads a separately generated, vetted JSON snapshot. This reduces browser privileges and keeps hosting static.
3. **Show a genuine interactive experience without fake source data.** A user-input-only calculator demonstrates percentage movement and regional deviation. It does not generate synthetic PIHPS market observations, store input, or bypass ingestion controls.

## Measurement definitions

Price movement: (current observation - previous comparable observation) / previous comparable observation.

Province deviation: (province price - mean of comparable province prices) / mean of comparable province prices.

Both are ratios, formatted as percentages only for display. Interpretation depends on commodity, unit, channel, date, and sampling coverage. The production pipeline must enforce the required consistency before using those numbers.

## Verification approach

- **Unit contracts:** Parsing, numerical validation, duplicates, mapping rules, schema constraints, warehouse operations.
- **Data integrity:** Revisions, conflicts, promotion quality, publish state, missing values.
- **Security:** Host allowlists, restricted BigQuery surfaces, plan-hash bootstrap approval, no credential-bearing site code.
- **Frontend:** Explicit empty/error states, keyboard and mobile navigation, four-input calculator with invalid-value tests.
- **CI:** GitHub Actions and GitLab hosted runners. A preview site should deploy only from GitLab's default branch after relevant checks pass.

Record PASS only after a real test or pipeline completed successfully. A green source probe is not evidence of published BigQuery data. Browser screenshots, public Pages reachability, and GitLab access-control settings must be verified separately.

## Constraints and limitations

- The initial version has no validated production snapshot. No price, trend, freshness, or province coverage statistics are claimed.
- The guarded PIHPS website interface can change without notice.
- The first cloud activation and mapping review are blocked on separate [issue #48](https://github.com/Fadhilstat/PanganLens/issues/48).
- GitHub and GitLab may have different commit IDs because the initial GitLab sync transferred file contents rather than Git history.
- Public static hosting does not imply continuously refreshed prices.

## Shipping checklist

1. Verify the full GitHub PR test and PIHPS source-probe jobs.
2. Verify GitLab MR pipeline and post-merge main pipeline.
3. Compare repository file trees and blob hashes.
4. Inspect the deployed URL without login and confirm calculator/empty states.
5. Record the public URL only when it has been successfully opened.
6. Keep cloud ingestion and dashboard refresh disabled until independent data-quality and readiness gates are satisfied.

## Next milestone

Activate the data path with a reviewed plan and short-lived identities, then publish a first verified snapshot with explicit coverage, revision history, and missing-data indicators. A public demo can be portfolio-ready before a live-data system is production-ready, provided the difference is clear.


## Sign-aware analytical semantics

The production UI's movement summary must not label the least-negative price change as a rise, or the least-positive change as a fall. A positive daily percentage can qualify as a rise and a negative value can qualify as a fall; a true zero belongs in neither category. Missing and malformed observations are excluded rather than coerced to zero.

For the regional comparison, a missing province-versus-average gap means the comparison is unavailable, not that the region exactly matches its average. A true numeric zero may appear as "setara rata-rata". Rows must also have a positive numeric price and a named province before ranking.

The metric selectors are pure functions with deterministic ordering and tests. They do not fabricate or backfill price data. This boundary matters especially when a previously empty dashboard begins receiving real curated snapshots.


## End-to-end publication integrity

The exporter checks for an active `SUCCESS` publish state before querying prices, and uses the active observation date to bound national and provincial data. An empty or invalid publish pointer cannot be silently interpreted as permission to display market values. The JSON writer refuses nonempty prices without valid metadata.

A standalone Python script validates the deploy artifact, and the browser repeats the schema, date, status, and freshness checks. The checked-in empty JSON remains legal, allowing a reliable portfolio preview without fake market observations. The rules are covered by pytest and Node tests; end-to-end GCP ingestion remains a separate, unverified activation step.

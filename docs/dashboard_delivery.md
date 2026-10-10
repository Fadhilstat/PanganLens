# Dual dashboard delivery

PanganLens uses one validated BigQuery mart for two presentation layers.

## 1. Looker Studio dashboard

Use the native BigQuery connector in Looker Studio and connect only to views in `panganlens_mart`.

Recommended data sources:

- `vw_looker_national_price_daily` for national trends and commodity exploration.
- `vw_looker_region_price_daily` for regional comparisons.
- `vw_looker_province_map` for province-level mapping.
- `vw_looker_publish_state` for freshness and publish metadata.
- `vw_looker_pipeline_health` for the Data & Methodology page.

Do not connect Looker Studio to `panganlens_raw`, `panganlens_staging`, or core fact tables directly. Dashboard formatting belongs in Looker Studio. Price values must remain numeric until presentation formatting is applied.

BigQuery usage through Looker Studio can incur BigQuery query charges. Keep the dashboard on curated views, use sensible date filters, and configure project cost controls before broad sharing.

## 2. Public website dashboard

The public website is under `website/`. It is a static site and does not contain Google Cloud credentials.

The browser reads `website/data/dashboard.json`. That file is produced by:

```bash
python scripts/export_dashboard_snapshot.py \
  --project-id YOUR_PROJECT_ID \
  --output website/data/dashboard.json
```

The exporter reads only dashboard-facing views in `panganlens_mart` and applies a maximum-bytes-billed ceiling. Exact BigQuery NUMERIC values are serialized as decimal strings so the snapshot itself does not lose numeric precision. Formatting happens in the browser.

The repository ships an empty snapshot instead of fabricated demo values. Until the first production snapshot is generated, the website clearly states that production data has not been published. A separate calculator on the website accepts four user-provided prices and computes changes without claiming any real PIHPS observations. It does not store user inputs or send them over the network.

## Publishing with GitHub Pages

`dashboard_pages.yml` packages the static `website/` directory and deploys it through GitHub Pages. The repository must have Pages configured to use GitHub Actions as its publishing source.

A normal push deploys the snapshot already present in the repository and does not contact Google Cloud. A manual workflow run can optionally refresh the snapshot from BigQuery first. The BigQuery refresh path uses direct Workload Identity Federation through these repository variables:

- `GCP_PROJECT_ID`
- `GCP_WIF_PROVIDER`

No service account and no service-account JSON key are required for this read-only refresh path. BigQuery refresh is accepted only from `main`.

The refresh remains manual until direct WIF, production mappings, and readiness are validated. After those gates are green, a daily refresh schedule can be considered without changing the website architecture.


## GitLab Pages portfolio preview

The GitLab pipeline checks both Python and JavaScript before publishing the static directory. The deploy_portfolio_site job uses pages.publish to publish website/ only from the default branch; it does not contact BigQuery, run ingestion, or require a VPS.

GitLab project access control was reported as private at the time of this portfolio preview implementation, even though the repository was public. Publishing artifacts does not guarantee anonymous access. Under GitLab **Settings > General > Visibility, project features, permissions**, check the Pages visibility setting and choose **Everyone with access** for a public project, then verify the actual Pages URL from **Deploy > Pages** in a logged-out browser. Do not assume a default Pages URL if GitLab uses a unique domain.

GitHub Pages is a second optional static publishing route. The existing dashboard_pages.yml workflow requires the repository's Pages source to be set to GitHub Actions; a push of the website does not prove that deployment succeeded. Check the actual workflow conclusion and published URL before adding a public link to a portfolio.

**Publication mode:** Portfolio preview only. No mock market data, no live-price claim. Warehouse activation and curated price publication remain separately approved operations.


## Verified release checkpoint (10 October 2026)

GitHub PR #67 passed quality CI #37974789018. GitLab MR !2 and main pipelines #2931785591 and #2931787912 passed, including static Pages deployment. Full file-content parity across the two repositories: 153/153 matching Git blob SHA values.

Anonymous Pages access is NOT_VERIFIED: the GitLab project reports pages_access_level private. Separately, GitHub Pages workflow #37974862397 failed at Configure Pages because repository Pages was not enabled (HTTP 404). Neither is evidence of failure of the dashboard source code. Make Pages public and validate an actual URL without authentication before advertising it as a live portfolio link.


## Publication-gated price export (release candidate, 10 October 2026)

The exporter reads the reviewed `vw_looker_publish_state` first. If no active pointer exists, it writes an empty snapshot and skips price queries. If publication metadata is invalid, the export fails before the website JSON is replaced. National history may include dates up to the active observation date; province rows must match that exact date.

The browser checks JSON schema version, array shapes, successful publication run, ISO observation date, and reviewed freshness labels before displaying a price. A stale but valid publication can still be shown with its existing warning label; missing or invalid provenance cannot.

Both the GitHub Pages and GitLab Pages deployment steps must run `python scripts/check_public_snapshot.py website/data/dashboard.json` before packaging the site. The website preview uses an intentionally empty JSON file and does not claim live PIHPS prices. This static validation is separate from BigQuery source, mapping, and operational checks.


## GitLab Pages public launch URL and verification

The owner identified the current unique Pages domain as [https://panganlens-679cd2.gitlab.io/](https://panganlens-679cd2.gitlab.io/). The website's canonical URL and Open Graph metadata point to this domain; they do not prove that it is publicly reachable.

After successful `main` deployment, GitLab runs `public_site_smoke`, a nonblocking, anonymous hosted request for the real HTML, CSS, three JavaScript files, and `data/dashboard.json`. It rejects off-domain sign-in redirects, missing assets, incompatible schema, and a price payload without a valid publish state. Inspect the smoke job result separately from the successful `deploy_portfolio_site` job.

At implementation time the GitLab project API continued to return `pages_access_level: private`, even after the owner reported changing the setting. The direct URL could not be fetched from the assistant's runtime, so do not record PASS until a hosted external check or unauthenticated browser proves reachability. This distinction is part of the release acceptance criteria.

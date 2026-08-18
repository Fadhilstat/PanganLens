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

The repository ships an empty snapshot instead of fabricated demo values. Until the first production snapshot is generated, the website clearly states that production data has not been published.

## Publishing with GitHub Pages

`dashboard_pages.yml` packages the static `website/` directory and deploys it through GitHub Pages. The repository must have Pages configured to use GitHub Actions as its publishing source.

A normal push deploys the snapshot already present in the repository. A manual workflow run can optionally refresh the snapshot from BigQuery first. The BigQuery refresh path uses Workload Identity Federation through these repository variables:

- `GCP_PROJECT_ID`
- `GCP_WIF_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

No service-account JSON key is stored in the repository.

The refresh remains manual until the WIF smoke test and production mappings are both validated. After those gates are green, a daily refresh schedule can be added without changing the website architecture.

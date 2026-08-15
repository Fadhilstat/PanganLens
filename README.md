# PanganLens Indonesia

PanganLens Indonesia is a public-data analytics project for monitoring food price movements across Indonesia. The project is being built as a maintainable data product with a validated BigQuery warehouse and a Looker Studio dashboard designed for clear public use.

## Current status

The project is in Phase 2: Technical Implementation. The current repository foundation focuses on data ingestion contracts, a normalized 3NF warehouse model, duplicate and conflict controls, and data quality checks before any record can reach the dashboard layer.

## Data source strategy

PIHPS Bank Indonesia is the primary food price source. The ingestion layer prioritizes a validated public data interface, then official report or download routes, with HTML scraping reserved as the last fallback. Undocumented website endpoints are not treated as stable public APIs until repeated live checks confirm their behavior.

## Repository map

```text
scripts/        Source probes and operational utilities
sql/            BigQuery datasets, 3NF core schema, and quality checks
src/panganlens/ Python package for domain, ingestion, validation, and warehouse logic
tests/          Automated tests for data contracts and repository rules
```

More complete project documentation will be written after the technical implementation is stable and validated.

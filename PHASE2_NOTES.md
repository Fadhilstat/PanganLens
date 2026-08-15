# PanganLens Phase 2.1 Foundation

This package is intentionally limited to the data foundation. It does not yet
promote an undocumented PIHPS website endpoint to a production API.

## What is included

- Provider-neutral ingestion contract
- PIHPS candidate endpoint probe
- Strict price observation model
- Source-independent business key
- Source-independent semantic record hash
- Exact duplicate classification
- Value conflict quarantine
- BigQuery 3NF DDL
- Raw, staging, and operations DDL
- Post-load data quality queries
- Tests that reject em dash characters in Python files

## Promotion rule for the PIHPS JSON route

The JSON route can become the first ingestion provider only after a live probe
returns HTTP 200, valid JSON, non-empty reference data, and a stable response
shape across repeated checks. Until then, it remains a candidate route and the
report or download path stays the fallback.

## Next implementation slice

1. Run the live PIHPS probe from a network that can reach bi.go.id.
2. Capture a small raw response for one date range.
3. Define the parser against the observed response shape.
4. Load normalized rows into staging.
5. Run duplicate, conflict, and referential checks.
6. Promote only validated rows into the 3NF core tables.

## Phase 2.2 live source evidence

The PIHPS website JSON routes remain an undocumented implementation detail.
Phase 2.2 adds a guarded client that accepts only row-oriented JSON responses
and rejects unexpected shapes before any normalization or warehouse load begins.

The repository also includes a schema-only live probe. It records row counts
and field names, but it does not publish source row values. The network probe
runs separately from deterministic unit tests so an external outage cannot be
mistaken for a code-quality failure.

The scheduled probe is set for 07:20 UTC on weekdays, which is 14:20 WIB. This
is intentionally after PIHPS states that its normal daily publication process
is expected to complete around 13:00 WIB. Historical revisions remain possible,
so later ingestion work must preserve revision history rather than silently
overwriting validated observations.

# PanganLens Phase 2 Technical Notes

Phase 2 is focused on proving a trustworthy data path before any production ingestion or dashboard refresh is scheduled. The repository now contains the guarded source client, warehouse contracts, mapping controls, promotion gates, readiness checks, and bootstrap safeguards needed for that path. The remaining work is mainly cloud activation and operational verification.

## Current implementation baseline

The current `main` branch includes:

- Provider-neutral ingestion contracts
- Guarded PIHPS website client
- HTTPS and source-host allowlist
- Redirect, content-type, and payload-size checks
- Request, schema, and payload SHA-256 fingerprints
- Strict dynamic-date PIHPS grid parser
- Source-independent business keys and semantic record hashes
- Exact duplicate classification
- Value conflict quarantine
- Revision history tables
- Canonical commodity and region mapping with explicit human review
- BigQuery 3NF core schema
- Raw, staging, operations, and data quality layers
- Pre-staging and post-load quality gates
- Controlled staging-to-core promotion
- Curated Looker Studio semantic views
- Central BigQuery schema and warehouse-location contracts
- Plan-first, hash-locked production bootstrap tooling
- Metadata-only bootstrap schema verification
- Full BigQuery readiness inspection
- Tests that reject em dash characters in Python files

## Source policy

PIHPS Bank Indonesia remains the primary food price source. The preferred route is the guarded JSON interface used by the official public website while it remains reachable and continues to match the reviewed schema contract.

The website route is not described as a stable public API. PanganLens therefore treats it as an implementation detail of the official site, not as a guaranteed API contract. Official report or download routes remain the next fallback, with HTML extraction reserved as the last option.

The official PIHPS website and FAQ were checked again on 19 August 2026 and were still reachable. The FAQ also confirms that data can be updated several times during the day and may be revised later in certain conditions. PanganLens keeps revision history and idempotent loading for this reason.

## Data publication rule

No row can reach the curated mart merely because it was downloaded successfully. Publication still requires all relevant gates to pass:

1. Source transport and schema checks pass.
2. Raw capture evidence and hashes are retained.
3. Parsed values pass structural and numeric validation.
4. Canonical commodity and region mappings are reviewed.
5. Duplicate and conflict checks are resolved.
6. Promotion rules succeed without bypassing quarantine.
7. Post-load assertions pass.
8. Publish state advances only after the run is valid.

Looker Studio must read curated mart objects only. Raw and staging data remain internal pipeline layers.

## Cloud activation checkpoint

The repository is not yet claiming production readiness. The next Phase 2 checkpoint is tracked in GitHub Issue #48 and must be completed in this order:

1. Configure direct Workload Identity Federation for the read-only GitHub Actions identity.
2. Run the manual GCP authentication smoke test from `main`.
3. Run BigQuery readiness and record the expected blocked reasons before bootstrap.
4. Generate and review the exact bootstrap `plan_sha256` without applying SQL.
5. Use a separately reviewed minimum-privilege write boundary for bootstrap. Do not expand the read-only principal for convenience.
6. Apply schema only with explicit `--apply` and the exact reviewed plan hash.
7. Run the metadata-only bootstrap verifier and require `SCHEMA_READY`.
8. Re-run full readiness.
9. Keep production ingestion and dashboard schedules disabled until mapping, source evidence, data quality, publish state, and mart checks are all green.

## Security boundary

The read-only verification identity remains separate from future write identities. No long-lived Google Cloud key is stored in the repository. Broad roles such as Owner, Editor, or BigQuery Admin are not part of the planned activation path.

The current design uses project-level `roles/bigquery.jobUser` only where query jobs need to run and dataset-level `roles/bigquery.dataViewer` for read access. Any future write role must be justified by the exact operation it supports and reviewed separately.

## Cost boundary

Cloud activation must remain compatible with the portfolio goal of avoiding mandatory operating cost. BigQuery usage, query volume, refresh frequency, and billing controls must be checked before recurring workloads are enabled. A technically successful workflow is not enough if it introduces an unnecessary recurring cost.

## Phase boundary

Phase 2 remains open until the cloud environment is verified and the trusted data path is proven end to end. Phase 3 documentation work should not replace unfinished operational evidence.

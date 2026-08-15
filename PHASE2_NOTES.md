# PanganLens Phase 2 Technical Notes

Phase 2 is building the trusted data path before dashboard development. The
current branch does not promote the PIHPS website route to a documented public
API. It treats the route as a guarded implementation detail of the official
public site.

## What is included

- Provider-neutral ingestion contract
- Guarded PIHPS website client
- HTTPS and source-host allowlist
- Redirect, content-type, and payload-size checks
- Request, schema, and payload SHA-256 fingerprints
- Strict dynamic-date PIHPS grid parser
- Source-independent business keys and semantic record hashes
- Exact duplicate classification
- Value conflict quarantine
- Revision history tables
- BigQuery 3NF core DDL
- Raw, staging, operations, and data quality DDL
- Pre-staging and post-load quality gates
- Curated Looker Studio semantic views
- Tests that reject em dash characters in Python files

## Live PIHPS evidence

Two GitHub-hosted live probes on 15 August 2026 returned the same reviewed schema:

- Province reference: 34 rows with `id` and `name`
- Commodity reference: 31 rows with `cat_id`, `denomination`, `id`, `name`, and `sort`
- Grid response: dynamic `DD/MM/YYYY` columns plus `level`, `name`, and `no`

The grid schema is normalized before fingerprinting so a new observation date
does not look like a schema change. Any new non-date field still fails closed and
requires review.

## Schedule

The source probe is scheduled daily at 11:00 UTC, which is 18:00 WIB. The daily
schedule runs the source probe only. Deterministic tests, Ruff, and compile checks
run on pull requests and manual workflow runs.

## Promotion rule

The website JSON route can remain the preferred source method only while live
probes return valid JSON, match the reviewed schema contract, and pass transport
and integrity checks. Report or download extraction remains the fallback path.

## Next implementation slice

1. Build canonical commodity and region mapping from reviewed PIHPS references.
2. Store exact raw captures and source evidence in BigQuery.
3. Parse grid cells into staging candidates without guessing canonical IDs.
4. Quarantine unmapped, invalid, duplicate, or conflicting rows.
5. Promote only validated rows into the 3NF core.
6. Refresh curated Looker Studio marts after all publication gates pass.

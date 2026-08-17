# BigQuery Loader Security Boundary

## Purpose

The warehouse writer handles trusted data after PIHPS transport and schema checks have passed. It does not make an external response trustworthy by itself.

## Authentication

Production automation must use short-lived Google Cloud credentials. GitHub Actions should authenticate with OpenID Connect and Google Cloud Workload Identity Federation.

Do not store a service account JSON key in:

- the repository
- GitHub Actions secrets
- local notebooks committed to GitHub
- application logs
- raw or staging tables

The loader uses Google Application Default Credentials. This keeps credential acquisition outside the Python code and allows the same writer to run locally, in GitHub Actions, or in a Google Cloud runtime without embedding secrets.

## Raw capture contract

A raw capture is accepted only when:

1. `capture_id` and `run_id` are present.
2. `captured_at` includes a timezone.
3. request, schema, and payload fingerprints are valid lowercase SHA-256 values.
4. `payload_bytes` matches the UTF-8 payload size.
5. `payload_sha256` matches the exact UTF-8 bytes written to BigQuery.

The BigQuery write uses `capture_id` as the idempotency key. A retry with the same `capture_id` and the same payload becomes a no-op. Reusing the same `capture_id` with a different payload hash fails before a new row can be inserted.

## Access scope

The ingestion identity should receive only the permissions required for its own datasets and query jobs. It must not receive project-wide Owner or Editor access.

The first deployment scope is limited to:

- writing `panganlens_raw`
- writing controlled operational records in `panganlens_ops`
- writing validated candidates in `panganlens_staging`
- running approved quality and promotion queries

Looker Studio remains read-only against `panganlens_mart` views.

## Promotion boundary

Writing a raw capture does not refresh the dashboard. Promotion remains a separate step after mapping, duplicate, conflict, revision, and referential checks pass. A failed run must leave the last known good mart state untouched.

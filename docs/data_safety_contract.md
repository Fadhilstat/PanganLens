# PanganLens Data Safety Contract

This document defines the boundary between external source data and the trusted
warehouse used by PanganLens.

## Source boundary

PIHPS Bank Indonesia is the primary source. The current website JSON route is an
implementation detail of the public site, not a documented API contract. It is
allowed only while repeated live probes continue to match the reviewed schema.

The client requires HTTPS, an allowlisted source host, JSON content, no HTTP
redirect, a bounded payload size, and a valid UTF-8 body. Each successful source
capture records request, schema, and payload fingerprints.

A successful capture is not treated as current forever. Production readiness also
checks the age of the latest successful PIHPS capture. The default freshness limit
is 72 hours. This gives a normal Friday-to-Monday gap room to pass while still
blocking a source that has stopped producing fresh evidence. Longer gaps, including
extended holidays or upstream outages, remain fail-closed and require an operator
to review source health before publication resumes.

## Raw integrity

The raw layer stores the exact decoded JSON text together with its SHA-256 hash.
Before normalization, the pipeline recomputes the hash and blocks the run if the
stored payload no longer matches the captured payload.

Raw data is immutable input evidence. It is never read by Looker Studio.

## Parsing and mapping

PIHPS grid date columns are dynamic and are parsed strictly as `DD/MM/YYYY`.
Prices remain missing when the source is missing. Missing values are never
replaced with zero.

A source row name is not a canonical region or market ID. Parsed rows must pass
an explicit mapping step before a business key can be created. Unmapped rows are
quarantined instead of being matched by guesswork.

## Duplicate, conflict, and revision rules

An exact duplicate has the same business key and the same semantic record hash.
It is logged and not inserted again.

A conflict has the same business key but different values within an unresolved
batch. It is quarantined and blocks publication.

A revision is a later source value for a previously validated business key. The
old and new record hashes are retained in revision history. The trusted core is
updated only after the revision rule accepts the new source value.

## Trusted warehouse boundary

Only rows with `mapping_status = MAPPED` and `validation_status = VALID` are
eligible for the 3NF core. A run must pass raw integrity, mapping, uniqueness,
conflict, referential, source freshness, and post-load checks before curated marts
are treated as publication-ready.

If a critical check fails, the dashboard keeps the last known good dataset.

## Looker Studio contract

Looker Studio reads only curated views in `panganlens_mart`. Prices stay numeric
in BigQuery so Looker Studio can sort, aggregate, calculate, and format currency
correctly. Human-readable labels and sort keys are added in the semantic views,
not by mutating the underlying facts.

The dashboard must never connect directly to raw or staging datasets.

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


## Public snapshot fail-closed gate

The curated publish pointer, not the mere presence of rows in price marts, decides whether prices can leave the warehouse. No active publish pointer means an empty website snapshot. A pointer with a non-SUCCESS status, unreviewed freshness label, or invalid observation date stops export.

National rows must not be newer than the pointer's active observation date. Province comparisons must refer to that same active observation date so the website cannot rank historical and current province observations together.

The website performs a second provenance check before rendering price values. GitHub Pages and GitLab Pages also run a dependency-free static JSON validation before deployment. These checks do not replace the source freshness, mapping, and warehouse quality controls already required for first production activation.


## Read-only source research capture

`scripts/export_pihps_research_sample.py` now supports a small source-data audit
without BigQuery. It validates the official PIHPS reference IDs, exact reviewed
transport/schema and raw payload SHA-256, parses positive price cells and missing
cells, fails on repeated source row keys, and retains original source labels and IDs
without inventing canonical mappings. Output CSV cells are protected against
spreadsheet formulas. All rows are marked `UNREVIEWED_SOURCE_SAMPLE`.

This is **not a production capture**. The CLI explicitly refuses to export into
`website/`, the GitHub scheduled probe never exports sample prices, and only
pull request/manual workflow runs retain temporary review artifacts (3 days).
A source audit passing means only that a narrow captured response was usable for
human mapping review, not that BigQuery has a fresh published dataset.

Never copy sample prices to `website/data/dashboard.json` without the existing
warehouse ingestion, reviewed mapping, quality, source freshness and publication
pointer checks. Raw source IDs and names must not be silently treated as canonical IDs.

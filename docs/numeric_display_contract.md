# Numeric and display contract

PanganLens keeps analytical values separate from presentation formatting.

## Core rule

Price values remain numeric from staging through core and curated mart views. The pipeline does not store formatted strings such as `Rp 62.650` as analytical measures.

Looker Studio is responsible for currency symbols, thousands separators, decimal display, and localized date labels.

## Accuracy rules

- Source prices are parsed with `Decimal` before warehouse persistence.
- BigQuery stores validated prices as `NUMERIC`.
- Core promotion does not apply `ROUND()` to source price values.
- Missing values are not converted to zero.
- Prices must be greater than zero when present.
- Exact duplicates may be collapsed only when both business key and record hash match.
- Different record hashes for the same business key are conflicts and block promotion.
- A later validated value for an existing core business key is stored as a source revision before the current core value changes.
- Dashboard-facing views preserve the underlying numeric measure and add labels separately.

## Looker Studio display

Recommended price display:

- Currency: Indonesian Rupiah
- Decimal places: 0 for source prices unless PIHPS begins publishing fractional rupiah values
- Thousands separator: enabled
- Abbreviated values: disabled for primary KPI cards when exact public values matter

A price of `62650` in BigQuery should therefore be displayed as `Rp62.650` or the equivalent locale-aware format without changing the stored value.

For percentages derived from prices, keep the calculation numeric and configure the visual layer to display an appropriate number of decimal places. Avoid pre-formatting percentages as strings in SQL.

## Publish gate

A dashboard refresh is blocked when any of the following is true:

- a business key has conflicting record hashes;
- an invalid or unmapped staging row remains in the run;
- a required numeric value is missing or non-positive;
- business-key uniqueness fails after deduplication;
- post-load fact uniqueness or referential integrity fails.

# Interactive Province Map

The regional dashboard uses `panganlens_mart.vw_looker_province_map` as the only map-facing data source.

## Recommended Looker Studio configuration

Use a Google Maps **Filled map**.

- Location: `map_location`
- Geographic type: Country subdivision, first level
- Country context: Indonesia
- Color metric: `price_idr` or `price_gap_vs_province_average_pct`
- Date range dimension: `observation_date`
- Cross-filtering: enabled

The map should act as a page-level interaction control. When a viewer clicks a province, Looker Studio applies that province as a cross-filter to the KPI cards, price trend, regional comparison, and detail table on the same page. The selected province should stay visually selected until the viewer clears the interaction.

## Visual behavior

Keep the map readable and restrained.

- Use a neutral base map.
- Use one sequential scale for absolute price.
- Use a diverging scale only for comparison metrics such as the gap versus the provincial average.
- Avoid rainbow palettes.
- Keep province borders visible but subtle.
- Show province name, current price, unit, observation date, and comparison value in the tooltip.
- Place a small `Reset pilihan` hint near the map so public users understand how to clear a selection.

## Data contract

The map view has one row per:

`observation_date + commodity_id + channel_id + province_id`

Only `region_level = 'province'` records are eligible. The view does not read raw or staging data and does not format prices into currency strings. Looker Studio owns display formatting while BigQuery retains numeric values for correct aggregation and sorting.

`map_location` intentionally uses the reviewed province name from the canonical region dimension. Do not manufacture ISO subdivision codes unless a separate verified mapping is added and quality checked.

## Interaction contract

The province map is the primary regional selector. The following components should share the same curated data source or compatible dimensions so cross-filtering remains predictable:

- Current province price KPI
- Gap versus benchmark KPI
- 30-day price trend
- Province ranking table
- Short contextual summary

A click on a province must never change the underlying warehouse state. It is only a report filter interaction.

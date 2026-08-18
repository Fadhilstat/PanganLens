WITH checks AS (
  SELECT
    'national_business_key_unique' AS check_name,
    (
      SELECT COUNT(*)
      FROM (
        SELECT 1
        FROM panganlens_core.food_price_national
        GROUP BY observation_date, commodity_id, channel_id
        HAVING COUNT(*) > 1
      )
    ) AS failure_count

  UNION ALL

  SELECT
    'region_business_key_unique',
    (
      SELECT COUNT(*)
      FROM (
        SELECT 1
        FROM panganlens_core.food_price_region
        GROUP BY observation_date, commodity_id, channel_id, region_id
        HAVING COUNT(*) > 1
      )
    )

  UNION ALL

  SELECT
    'market_business_key_unique',
    (
      SELECT COUNT(*)
      FROM (
        SELECT 1
        FROM panganlens_core.food_price_market
        GROUP BY observation_date, commodity_id, market_id
        HAVING COUNT(*) > 1
      )
    )

  UNION ALL

  SELECT
    'national_prices_have_known_commodities',
    COUNTIF(c.commodity_id IS NULL)
  FROM panganlens_core.food_price_national AS f
  LEFT JOIN panganlens_core.commodity AS c
    ON f.commodity_id = c.commodity_id

  UNION ALL

  SELECT
    'national_prices_have_known_channels',
    COUNTIF(c.channel_id IS NULL)
  FROM panganlens_core.food_price_national AS f
  LEFT JOIN panganlens_core.market_channel AS c
    ON f.channel_id = c.channel_id

  UNION ALL

  SELECT
    'region_prices_have_known_commodities',
    COUNTIF(c.commodity_id IS NULL)
  FROM panganlens_core.food_price_region AS f
  LEFT JOIN panganlens_core.commodity AS c
    ON f.commodity_id = c.commodity_id

  UNION ALL

  SELECT
    'region_prices_have_known_channels',
    COUNTIF(c.channel_id IS NULL)
  FROM panganlens_core.food_price_region AS f
  LEFT JOIN panganlens_core.market_channel AS c
    ON f.channel_id = c.channel_id

  UNION ALL

  SELECT
    'region_prices_have_known_regions',
    COUNTIF(r.region_id IS NULL)
  FROM panganlens_core.food_price_region AS f
  LEFT JOIN panganlens_core.region AS r
    ON f.region_id = r.region_id

  UNION ALL

  SELECT
    'market_prices_have_known_commodities',
    COUNTIF(c.commodity_id IS NULL)
  FROM panganlens_core.food_price_market AS f
  LEFT JOIN panganlens_core.commodity AS c
    ON f.commodity_id = c.commodity_id

  UNION ALL

  SELECT
    'market_prices_have_known_markets',
    COUNTIF(m.market_id IS NULL)
  FROM panganlens_core.food_price_market AS f
  LEFT JOIN panganlens_core.market AS m
    ON f.market_id = m.market_id

  UNION ALL

  SELECT
    'all_core_prices_positive',
    (
      SELECT COUNTIF(price <= 0)
      FROM (
        SELECT price FROM panganlens_core.food_price_national
        UNION ALL
        SELECT price FROM panganlens_core.food_price_region
        UNION ALL
        SELECT price FROM panganlens_core.food_price_market
      )
    )

  UNION ALL

  SELECT
    'dimension_primary_keys_unique',
    (
      SELECT SUM(duplicate_groups)
      FROM (
        SELECT COUNT(*) AS duplicate_groups
        FROM (
          SELECT 1 FROM panganlens_core.commodity_category
          GROUP BY category_id HAVING COUNT(*) > 1
        )
        UNION ALL
        SELECT COUNT(*) FROM (
          SELECT 1 FROM panganlens_core.unit
          GROUP BY unit_id HAVING COUNT(*) > 1
        )
        UNION ALL
        SELECT COUNT(*) FROM (
          SELECT 1 FROM panganlens_core.market_channel
          GROUP BY channel_id HAVING COUNT(*) > 1
        )
        UNION ALL
        SELECT COUNT(*) FROM (
          SELECT 1 FROM panganlens_core.commodity
          GROUP BY commodity_id HAVING COUNT(*) > 1
        )
        UNION ALL
        SELECT COUNT(*) FROM (
          SELECT 1 FROM panganlens_core.region
          GROUP BY region_id HAVING COUNT(*) > 1
        )
        UNION ALL
        SELECT COUNT(*) FROM (
          SELECT 1 FROM panganlens_core.market
          GROUP BY market_id HAVING COUNT(*) > 1
        )
      )
    )

  UNION ALL

  SELECT
    'commodity_foreign_keys_valid',
    COUNTIF(category.category_id IS NULL OR unit_ref.unit_id IS NULL)
  FROM panganlens_core.commodity AS commodity
  LEFT JOIN panganlens_core.commodity_category AS category
    ON commodity.category_id = category.category_id
  LEFT JOIN panganlens_core.unit AS unit_ref
    ON commodity.unit_id = unit_ref.unit_id

  UNION ALL

  SELECT
    'market_foreign_keys_valid',
    COUNTIF(region.region_id IS NULL OR channel.channel_id IS NULL)
  FROM panganlens_core.market AS market
  LEFT JOIN panganlens_core.region AS region
    ON market.region_id = region.region_id
  LEFT JOIN panganlens_core.market_channel AS channel
    ON market.channel_id = channel.channel_id

  UNION ALL

  SELECT
    'region_parent_references_valid',
    COUNTIF(child.parent_region_id IS NOT NULL AND parent.region_id IS NULL)
  FROM panganlens_core.region AS child
  LEFT JOIN panganlens_core.region AS parent
    ON child.parent_region_id = parent.region_id

  UNION ALL

  SELECT
    'core_source_capture_references_valid',
    COUNTIF(capture.capture_id IS NULL)
  FROM (
    SELECT source_capture_id FROM panganlens_core.food_price_national
    UNION ALL
    SELECT source_capture_id FROM panganlens_core.food_price_region
    UNION ALL
    SELECT source_capture_id FROM panganlens_core.food_price_market
  ) AS fact
  LEFT JOIN panganlens_ops.source_capture AS capture
    ON fact.source_capture_id = capture.capture_id

  UNION ALL

  SELECT
    'unresolved_conflicts_zero',
    COUNTIF(resolution_status = 'OPEN')
  FROM panganlens_ops.conflict_log
)
SELECT
  check_name,
  failure_count,
  IF(failure_count = 0, 'PASS', 'FAIL') AS status
FROM checks
ORDER BY check_name;

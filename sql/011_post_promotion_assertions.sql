-- Run inside the same transaction as core promotion.
-- Any failed assertion rolls back the promotion query.

ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT observation_date, commodity_id, channel_id
    FROM panganlens_core.food_price_national
    GROUP BY observation_date, commodity_id, channel_id
    HAVING COUNT(*) > 1
  )
) AS 'post-promotion check failed: national business key is not unique';

ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT observation_date, commodity_id, channel_id, region_id
    FROM panganlens_core.food_price_region
    GROUP BY observation_date, commodity_id, channel_id, region_id
    HAVING COUNT(*) > 1
  )
) AS 'post-promotion check failed: region business key is not unique';

ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT observation_date, commodity_id, market_id
    FROM panganlens_core.food_price_market
    GROUP BY observation_date, commodity_id, market_id
    HAVING COUNT(*) > 1
  )
) AS 'post-promotion check failed: market business key is not unique';

ASSERT (
  SELECT COUNTIF(price <= 0) = 0
  FROM (
    SELECT price FROM panganlens_core.food_price_national
    UNION ALL
    SELECT price FROM panganlens_core.food_price_region
    UNION ALL
    SELECT price FROM panganlens_core.food_price_market
  )
) AS 'post-promotion check failed: core contains a non-positive price';

ASSERT (
  SELECT COUNTIF(commodity.commodity_id IS NULL) = 0
  FROM panganlens_core.food_price_region AS fact
  LEFT JOIN panganlens_core.commodity AS commodity
    ON fact.commodity_id = commodity.commodity_id
) AS 'post-promotion check failed: region price has an unknown commodity';

ASSERT (
  SELECT COUNTIF(region.region_id IS NULL) = 0
  FROM panganlens_core.food_price_region AS fact
  LEFT JOIN panganlens_core.region AS region
    ON fact.region_id = region.region_id
) AS 'post-promotion check failed: region price has an unknown region';

ASSERT (
  SELECT COUNTIF(market.market_id IS NULL) = 0
  FROM panganlens_core.food_price_market AS fact
  LEFT JOIN panganlens_core.market AS market
    ON fact.market_id = market.market_id
) AS 'post-promotion check failed: market price has an unknown market';

ASSERT (
  SELECT COUNTIF(capture.capture_id IS NULL) = 0
  FROM (
    SELECT source_capture_id FROM panganlens_core.food_price_national
    UNION ALL
    SELECT source_capture_id FROM panganlens_core.food_price_region
    UNION ALL
    SELECT source_capture_id FROM panganlens_core.food_price_market
  ) AS fact
  LEFT JOIN panganlens_ops.source_capture AS capture
    ON fact.source_capture_id = capture.capture_id
) AS 'post-promotion check failed: core source capture reference is invalid';

ASSERT (
  SELECT COUNTIF(resolution_status = 'OPEN') = 0
  FROM panganlens_ops.conflict_log
) AS 'post-promotion check failed: unresolved conflicts remain';

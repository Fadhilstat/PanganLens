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
  SELECT COUNT(*) = 0
  FROM (
    SELECT 1 FROM panganlens_core.commodity_category
    GROUP BY category_id HAVING COUNT(*) > 1
    UNION ALL
    SELECT 1 FROM panganlens_core.unit
    GROUP BY unit_id HAVING COUNT(*) > 1
    UNION ALL
    SELECT 1 FROM panganlens_core.market_channel
    GROUP BY channel_id HAVING COUNT(*) > 1
    UNION ALL
    SELECT 1 FROM panganlens_core.commodity
    GROUP BY commodity_id HAVING COUNT(*) > 1
    UNION ALL
    SELECT 1 FROM panganlens_core.region
    GROUP BY region_id HAVING COUNT(*) > 1
    UNION ALL
    SELECT 1 FROM panganlens_core.market
    GROUP BY market_id HAVING COUNT(*) > 1
  )
) AS 'post-promotion check failed: a dimension primary key is not unique';

ASSERT (
  SELECT COUNTIF(category.category_id IS NULL OR unit_ref.unit_id IS NULL) = 0
  FROM panganlens_core.commodity AS commodity
  LEFT JOIN panganlens_core.commodity_category AS category
    ON commodity.category_id = category.category_id
  LEFT JOIN panganlens_core.unit AS unit_ref
    ON commodity.unit_id = unit_ref.unit_id
) AS 'post-promotion check failed: commodity foreign key is invalid';

ASSERT (
  SELECT COUNTIF(region.region_id IS NULL OR channel.channel_id IS NULL) = 0
  FROM panganlens_core.market AS market
  LEFT JOIN panganlens_core.region AS region
    ON market.region_id = region.region_id
  LEFT JOIN panganlens_core.market_channel AS channel
    ON market.channel_id = channel.channel_id
) AS 'post-promotion check failed: market foreign key is invalid';

ASSERT (
  SELECT COUNTIF(child.parent_region_id IS NOT NULL AND parent.region_id IS NULL) = 0
  FROM panganlens_core.region AS child
  LEFT JOIN panganlens_core.region AS parent
    ON child.parent_region_id = parent.region_id
) AS 'post-promotion check failed: region parent reference is invalid';

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
  FROM panganlens_core.food_price_national AS fact
  LEFT JOIN panganlens_core.commodity AS commodity
    ON fact.commodity_id = commodity.commodity_id
) AS 'post-promotion check failed: national price has an unknown commodity';

ASSERT (
  SELECT COUNTIF(channel.channel_id IS NULL) = 0
  FROM panganlens_core.food_price_national AS fact
  LEFT JOIN panganlens_core.market_channel AS channel
    ON fact.channel_id = channel.channel_id
) AS 'post-promotion check failed: national price has an unknown channel';

ASSERT (
  SELECT COUNTIF(commodity.commodity_id IS NULL) = 0
  FROM panganlens_core.food_price_region AS fact
  LEFT JOIN panganlens_core.commodity AS commodity
    ON fact.commodity_id = commodity.commodity_id
) AS 'post-promotion check failed: region price has an unknown commodity';

ASSERT (
  SELECT COUNTIF(channel.channel_id IS NULL) = 0
  FROM panganlens_core.food_price_region AS fact
  LEFT JOIN panganlens_core.market_channel AS channel
    ON fact.channel_id = channel.channel_id
) AS 'post-promotion check failed: region price has an unknown channel';

ASSERT (
  SELECT COUNTIF(region.region_id IS NULL) = 0
  FROM panganlens_core.food_price_region AS fact
  LEFT JOIN panganlens_core.region AS region
    ON fact.region_id = region.region_id
) AS 'post-promotion check failed: region price has an unknown region';

ASSERT (
  SELECT COUNTIF(commodity.commodity_id IS NULL) = 0
  FROM panganlens_core.food_price_market AS fact
  LEFT JOIN panganlens_core.commodity AS commodity
    ON fact.commodity_id = commodity.commodity_id
) AS 'post-promotion check failed: market price has an unknown commodity';

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

ASSERT (
  SELECT COUNT(*) = 0
  FROM promotion_batch AS batch
  LEFT JOIN panganlens_core.food_price_national AS fact
    ON batch.scope = 'national'
    AND fact.observation_date = batch.observation_date
    AND fact.commodity_id = batch.commodity_id
    AND fact.channel_id = batch.channel_id
    AND fact.record_hash = batch.record_hash
  WHERE batch.scope = 'national'
    AND fact.record_hash IS NULL
) AS 'post-promotion reconciliation failed: national row missing from core';

ASSERT (
  SELECT COUNT(*) = 0
  FROM promotion_batch AS batch
  LEFT JOIN panganlens_core.food_price_region AS fact
    ON batch.scope = 'region'
    AND fact.observation_date = batch.observation_date
    AND fact.commodity_id = batch.commodity_id
    AND fact.channel_id = batch.channel_id
    AND fact.region_id = batch.region_id
    AND fact.record_hash = batch.record_hash
  WHERE batch.scope = 'region'
    AND fact.record_hash IS NULL
) AS 'post-promotion reconciliation failed: region row missing from core';

ASSERT (
  SELECT COUNT(*) = 0
  FROM promotion_batch AS batch
  LEFT JOIN panganlens_core.food_price_market AS fact
    ON batch.scope = 'market'
    AND fact.observation_date = batch.observation_date
    AND fact.commodity_id = batch.commodity_id
    AND fact.market_id = batch.market_id
    AND fact.record_hash = batch.record_hash
  WHERE batch.scope = 'market'
    AND fact.record_hash IS NULL
) AS 'post-promotion reconciliation failed: market row missing from core';

-- Supply @run_id as a named STRING query parameter.
-- Promotion is fail-closed. Any unresolved duplicate conflict blocks all fact writes.

ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT
      business_key_hash
    FROM panganlens_staging.normalized_price_candidate
    WHERE run_id = @run_id
      AND mapping_status = 'MAPPED'
      AND validation_status = 'VALID'
    GROUP BY business_key_hash
    HAVING COUNT(DISTINCT record_hash) > 1
  )
) AS 'promotion blocked: conflicting values share a business key';

ASSERT (
  SELECT COUNT(*) = 0
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id
    AND (
      mapping_status != 'MAPPED'
      OR validation_status != 'VALID'
      OR business_key_hash IS NULL
      OR record_hash IS NULL
      OR price <= 0
    )
) AS 'promotion blocked: staging contains unmapped or invalid rows';

CREATE TEMP TABLE promotion_batch AS
SELECT * EXCEPT(duplicate_rank)
FROM (
  SELECT
    candidate.*,
    ROW_NUMBER() OVER (
      PARTITION BY business_key_hash, record_hash
      ORDER BY capture_id, source_row_no
    ) AS duplicate_rank
  FROM panganlens_staging.normalized_price_candidate AS candidate
  WHERE run_id = @run_id
    AND mapping_status = 'MAPPED'
    AND validation_status = 'VALID'
)
WHERE duplicate_rank = 1;

ASSERT (
  SELECT COUNT(*) = COUNT(DISTINCT business_key_hash)
  FROM promotion_batch
) AS 'promotion blocked: deduplicated batch is not unique by business key';

INSERT INTO panganlens_ops.revision_history (
  revision_id,
  business_key_hash,
  old_record_hash,
  new_record_hash,
  old_price,
  new_price,
  old_capture_id,
  new_capture_id,
  detected_at,
  resolution_status,
  resolution_note
)
SELECT
  TO_HEX(SHA256(CONCAT(
    batch.business_key_hash,
    '|',
    current_fact.record_hash,
    '|',
    batch.record_hash
  ))) AS revision_id,
  batch.business_key_hash,
  current_fact.record_hash,
  batch.record_hash,
  current_fact.price,
  batch.price,
  current_fact.source_capture_id,
  batch.capture_id,
  CURRENT_TIMESTAMP(),
  'ACCEPTED_SOURCE_REVISION',
  'PIHPS returned a different validated value for an existing business key.'
FROM promotion_batch AS batch
INNER JOIN panganlens_core.food_price_national AS current_fact
  ON batch.scope = 'national'
  AND current_fact.observation_date = batch.observation_date
  AND current_fact.commodity_id = batch.commodity_id
  AND current_fact.channel_id = batch.channel_id
WHERE current_fact.record_hash != batch.record_hash
  AND NOT EXISTS (
    SELECT 1
    FROM panganlens_ops.revision_history AS history
    WHERE history.business_key_hash = batch.business_key_hash
      AND history.old_record_hash = current_fact.record_hash
      AND history.new_record_hash = batch.record_hash
  );

INSERT INTO panganlens_ops.revision_history (
  revision_id,
  business_key_hash,
  old_record_hash,
  new_record_hash,
  old_price,
  new_price,
  old_capture_id,
  new_capture_id,
  detected_at,
  resolution_status,
  resolution_note
)
SELECT
  TO_HEX(SHA256(CONCAT(
    batch.business_key_hash,
    '|',
    current_fact.record_hash,
    '|',
    batch.record_hash
  ))),
  batch.business_key_hash,
  current_fact.record_hash,
  batch.record_hash,
  current_fact.price,
  batch.price,
  current_fact.source_capture_id,
  batch.capture_id,
  CURRENT_TIMESTAMP(),
  'ACCEPTED_SOURCE_REVISION',
  'PIHPS returned a different validated value for an existing business key.'
FROM promotion_batch AS batch
INNER JOIN panganlens_core.food_price_region AS current_fact
  ON batch.scope = 'region'
  AND current_fact.observation_date = batch.observation_date
  AND current_fact.commodity_id = batch.commodity_id
  AND current_fact.channel_id = batch.channel_id
  AND current_fact.region_id = batch.region_id
WHERE current_fact.record_hash != batch.record_hash
  AND NOT EXISTS (
    SELECT 1
    FROM panganlens_ops.revision_history AS history
    WHERE history.business_key_hash = batch.business_key_hash
      AND history.old_record_hash = current_fact.record_hash
      AND history.new_record_hash = batch.record_hash
  );

INSERT INTO panganlens_ops.revision_history (
  revision_id,
  business_key_hash,
  old_record_hash,
  new_record_hash,
  old_price,
  new_price,
  old_capture_id,
  new_capture_id,
  detected_at,
  resolution_status,
  resolution_note
)
SELECT
  TO_HEX(SHA256(CONCAT(
    batch.business_key_hash,
    '|',
    current_fact.record_hash,
    '|',
    batch.record_hash
  ))),
  batch.business_key_hash,
  current_fact.record_hash,
  batch.record_hash,
  current_fact.price,
  batch.price,
  current_fact.source_capture_id,
  batch.capture_id,
  CURRENT_TIMESTAMP(),
  'ACCEPTED_SOURCE_REVISION',
  'PIHPS returned a different validated value for an existing business key.'
FROM promotion_batch AS batch
INNER JOIN panganlens_core.food_price_market AS current_fact
  ON batch.scope = 'market'
  AND current_fact.observation_date = batch.observation_date
  AND current_fact.commodity_id = batch.commodity_id
  AND current_fact.market_id = batch.market_id
WHERE current_fact.record_hash != batch.record_hash
  AND NOT EXISTS (
    SELECT 1
    FROM panganlens_ops.revision_history AS history
    WHERE history.business_key_hash = batch.business_key_hash
      AND history.old_record_hash = current_fact.record_hash
      AND history.new_record_hash = batch.record_hash
  );

MERGE panganlens_core.food_price_national AS target
USING (
  SELECT *
  FROM promotion_batch
  WHERE scope = 'national'
) AS source
ON target.observation_date = source.observation_date
AND target.commodity_id = source.commodity_id
AND target.channel_id = source.channel_id
WHEN MATCHED AND target.record_hash != source.record_hash THEN
  UPDATE SET
    price = source.price,
    source_capture_id = source.capture_id,
    record_hash = source.record_hash,
    loaded_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    observation_date,
    commodity_id,
    channel_id,
    price,
    source_capture_id,
    record_hash,
    loaded_at
  )
  VALUES (
    source.observation_date,
    source.commodity_id,
    source.channel_id,
    source.price,
    source.capture_id,
    source.record_hash,
    CURRENT_TIMESTAMP()
  );

MERGE panganlens_core.food_price_region AS target
USING (
  SELECT *
  FROM promotion_batch
  WHERE scope = 'region'
) AS source
ON target.observation_date = source.observation_date
AND target.commodity_id = source.commodity_id
AND target.channel_id = source.channel_id
AND target.region_id = source.region_id
WHEN MATCHED AND target.record_hash != source.record_hash THEN
  UPDATE SET
    price = source.price,
    source_capture_id = source.capture_id,
    record_hash = source.record_hash,
    loaded_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    observation_date,
    commodity_id,
    channel_id,
    region_id,
    price,
    source_capture_id,
    record_hash,
    loaded_at
  )
  VALUES (
    source.observation_date,
    source.commodity_id,
    source.channel_id,
    source.region_id,
    source.price,
    source.capture_id,
    source.record_hash,
    CURRENT_TIMESTAMP()
  );

MERGE panganlens_core.food_price_market AS target
USING (
  SELECT *
  FROM promotion_batch
  WHERE scope = 'market'
) AS source
ON target.observation_date = source.observation_date
AND target.commodity_id = source.commodity_id
AND target.market_id = source.market_id
WHEN MATCHED AND target.record_hash != source.record_hash THEN
  UPDATE SET
    price = source.price,
    source_capture_id = source.capture_id,
    record_hash = source.record_hash,
    loaded_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    observation_date,
    commodity_id,
    market_id,
    price,
    source_capture_id,
    record_hash,
    loaded_at
  )
  VALUES (
    source.observation_date,
    source.commodity_id,
    source.market_id,
    source.price,
    source.capture_id,
    source.record_hash,
    CURRENT_TIMESTAMP()
  );

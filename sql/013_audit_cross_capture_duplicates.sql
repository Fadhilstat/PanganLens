-- Supply @run_id as a named STRING query parameter.
-- Log exact duplicates and conflicts across captures before promotion checks run.

INSERT INTO panganlens_ops.duplicate_log (
  run_id,
  business_key_hash,
  record_hash,
  kept_capture_id,
  duplicate_capture_id,
  detected_at
)
SELECT
  @run_id,
  grouped.business_key_hash,
  grouped.record_hash,
  grouped.kept_capture_id,
  duplicate_capture_id,
  CURRENT_TIMESTAMP()
FROM (
  SELECT
    business_key_hash,
    record_hash,
    MIN(capture_id) AS kept_capture_id,
    ARRAY_AGG(DISTINCT capture_id ORDER BY capture_id) AS capture_ids
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id
    AND mapping_status = 'MAPPED'
    AND validation_status = 'VALID'
    AND business_key_hash IS NOT NULL
    AND record_hash IS NOT NULL
  GROUP BY business_key_hash, record_hash
  HAVING COUNT(DISTINCT capture_id) > 1
) AS grouped
CROSS JOIN UNNEST(grouped.capture_ids) AS duplicate_capture_id
WHERE duplicate_capture_id != grouped.kept_capture_id
  AND NOT EXISTS (
    SELECT 1
    FROM panganlens_ops.duplicate_log AS existing
    WHERE existing.run_id = @run_id
      AND existing.business_key_hash = grouped.business_key_hash
      AND existing.record_hash = grouped.record_hash
      AND existing.kept_capture_id = grouped.kept_capture_id
      AND existing.duplicate_capture_id = duplicate_capture_id
  );

INSERT INTO panganlens_ops.conflict_log (
  conflict_id,
  run_id,
  business_key_hash,
  conflicting_record_hashes,
  conflict_payload,
  resolution_status,
  detected_at,
  resolved_at,
  resolution_note
)
SELECT
  TO_HEX(SHA256(CONCAT(
    @run_id,
    '|',
    business_key_hash,
    '|',
    ARRAY_TO_STRING(record_hashes, '|')
  ))) AS conflict_id,
  @run_id,
  business_key_hash,
  record_hashes,
  JSON_OBJECT(
    'reason', 'different validated records share one business key',
    'capture_count', capture_count,
    'record_count', ARRAY_LENGTH(record_hashes)
  ) AS conflict_payload,
  'OPEN',
  CURRENT_TIMESTAMP(),
  NULL,
  NULL
FROM (
  SELECT
    business_key_hash,
    ARRAY_AGG(DISTINCT record_hash ORDER BY record_hash) AS record_hashes,
    COUNT(DISTINCT capture_id) AS capture_count
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id
    AND mapping_status = 'MAPPED'
    AND validation_status = 'VALID'
    AND business_key_hash IS NOT NULL
    AND record_hash IS NOT NULL
  GROUP BY business_key_hash
  HAVING COUNT(DISTINCT record_hash) > 1
) AS conflicts
WHERE NOT EXISTS (
  SELECT 1
  FROM panganlens_ops.conflict_log AS existing
  WHERE existing.conflict_id = TO_HEX(SHA256(CONCAT(
    @run_id,
    '|',
    conflicts.business_key_hash,
    '|',
    ARRAY_TO_STRING(conflicts.record_hashes, '|')
  )))
);

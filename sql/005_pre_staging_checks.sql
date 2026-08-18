-- Supply @run_id as a named STRING query parameter.
WITH checks AS (
  SELECT
    'raw_payload_hash_valid' AS check_name,
    COUNTIF(
      LOWER(TO_HEX(SHA256(payload_text))) != LOWER(payload_sha256)
    ) AS failure_count
  FROM panganlens_raw.raw_food_price_capture
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'raw_payload_size_valid',
    COUNTIF(BYTE_LENGTH(payload_text) != payload_bytes)
  FROM panganlens_raw.raw_food_price_capture
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'capture_fingerprints_present',
    COUNTIF(
      LENGTH(request_fingerprint) != 64
      OR LENGTH(schema_fingerprint) != 64
      OR payload_sha256 IS NULL
      OR LENGTH(payload_sha256) != 64
    )
  FROM panganlens_ops.source_capture
  WHERE run_id = @run_id
    AND status = 'SUCCESS'

  UNION ALL

  SELECT
    'capture_source_host_allowlisted',
    COUNTIF(source_host != 'www.bi.go.id')
  FROM panganlens_ops.source_capture
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'staging_unmapped_rows_zero',
    COUNTIF(mapping_status != 'MAPPED')
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'staging_invalid_rows_zero',
    COUNTIF(validation_status != 'VALID')
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'staging_mapping_evidence_present',
    COUNTIF(
      mapping_status = 'MAPPED'
      AND (
        mapping_version IS NULL
        OR mapping_version <= 0
        OR mapping_key_fingerprint IS NULL
        OR LENGTH(mapping_key_fingerprint) != 64
      )
    )
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'staging_business_keys_present',
    COUNTIF(
      business_key_hash IS NULL
      OR record_hash IS NULL
      OR LENGTH(business_key_hash) != 64
      OR LENGTH(record_hash) != 64
    )
  FROM panganlens_staging.normalized_price_candidate
  WHERE run_id = @run_id

  UNION ALL

  SELECT
    'staging_business_key_conflicts_zero',
    COUNT(*)
  FROM (
    SELECT business_key_hash
    FROM panganlens_staging.normalized_price_candidate
    WHERE run_id = @run_id
      AND mapping_status = 'MAPPED'
      AND validation_status = 'VALID'
    GROUP BY business_key_hash
    HAVING COUNT(DISTINCT record_hash) > 1
  )

  UNION ALL

  SELECT
    'unresolved_run_conflicts_zero',
    COUNTIF(resolution_status = 'OPEN')
  FROM panganlens_ops.conflict_log
  WHERE run_id = @run_id
)
SELECT
  check_name,
  failure_count,
  IF(failure_count = 0, 'PASS', 'FAIL') AS status
FROM checks
ORDER BY check_name;

CREATE TABLE IF NOT EXISTS panganlens_ops.source_entity_mapping (
  source_system STRING NOT NULL,
  entity_type STRING NOT NULL,
  source_id STRING,
  source_name_normalized STRING,
  source_level STRING,
  parent_source_id STRING,
  canonical_id STRING NOT NULL,
  mapping_version INT64 NOT NULL,
  mapping_status STRING NOT NULL,
  reviewed_at TIMESTAMP NOT NULL,
  reviewed_by STRING NOT NULL,
  valid_from TIMESTAMP NOT NULL,
  valid_to TIMESTAMP,
  mapping_note STRING
)
CLUSTER BY source_system, entity_type, canonical_id;

-- This view exposes only active reviewed mappings to ingestion jobs.
CREATE OR REPLACE VIEW panganlens_ops.vw_active_source_entity_mapping AS
SELECT
  source_system,
  entity_type,
  source_id,
  source_name_normalized,
  source_level,
  parent_source_id,
  canonical_id,
  mapping_version,
  reviewed_at,
  reviewed_by
FROM panganlens_ops.source_entity_mapping
WHERE mapping_status = 'ACTIVE'
  AND valid_from <= CURRENT_TIMESTAMP()
  AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP());

-- BigQuery does not enforce uniqueness, so this check must return zero rows.
SELECT
  source_system,
  entity_type,
  source_id,
  source_name_normalized,
  source_level,
  parent_source_id,
  COUNT(*) AS active_mapping_count
FROM panganlens_ops.vw_active_source_entity_mapping
GROUP BY
  source_system,
  entity_type,
  source_id,
  source_name_normalized,
  source_level,
  parent_source_id
HAVING COUNT(*) > 1;

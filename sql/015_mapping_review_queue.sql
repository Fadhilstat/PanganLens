CREATE TABLE IF NOT EXISTS panganlens_ops.source_mapping_review_candidate (
  candidate_fingerprint STRING NOT NULL,
  source_system STRING NOT NULL,
  entity_type STRING NOT NULL,
  source_id STRING,
  source_name_normalized STRING,
  source_level STRING,
  parent_source_id STRING,
  mapping_version INT64 NOT NULL,
  review_status STRING NOT NULL,
  proposed_canonical_id STRING,
  evidence_capture_id STRING NOT NULL,
  source_schema_fingerprint STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  last_seen_at TIMESTAMP NOT NULL,
  reviewed_at TIMESTAMP,
  reviewed_by STRING,
  review_note STRING
)
CLUSTER BY review_status, entity_type, mapping_version;

CREATE OR REPLACE VIEW panganlens_ops.vw_mapping_review_queue AS
SELECT
  candidate_fingerprint,
  source_system,
  entity_type,
  source_id,
  source_name_normalized,
  source_level,
  parent_source_id,
  mapping_version,
  review_status,
  proposed_canonical_id,
  evidence_capture_id,
  source_schema_fingerprint,
  created_at,
  last_seen_at,
  reviewed_at,
  reviewed_by,
  review_note
FROM panganlens_ops.source_mapping_review_candidate
WHERE review_status = 'REVIEW_REQUIRED';

SELECT
  candidate_fingerprint,
  COUNT(*) AS candidate_count
FROM panganlens_ops.source_mapping_review_candidate
GROUP BY candidate_fingerprint
HAVING COUNT(*) > 1;

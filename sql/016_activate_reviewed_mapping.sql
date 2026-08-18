BEGIN TRANSACTION;

ASSERT (
  SELECT COUNT(*) = 1
  FROM panganlens_ops.source_mapping_review_candidate
  WHERE candidate_fingerprint = @candidate_fingerprint
    AND review_status = 'REVIEW_REQUIRED'
) AS 'mapping candidate must exist exactly once and require review';

ASSERT LENGTH(TRIM(@canonical_id)) > 0
AS 'canonical_id must not be empty';

ASSERT LENGTH(TRIM(@reviewed_by)) > 0
AS 'reviewed_by must not be empty';

ASSERT (
  SELECT COUNT(*) = 1
  FROM panganlens_ops.source_mapping_review_candidate AS candidate
  JOIN panganlens_ops.source_capture AS capture
    ON capture.capture_id = candidate.evidence_capture_id
   AND capture.schema_fingerprint = candidate.source_schema_fingerprint
  WHERE candidate.candidate_fingerprint = @candidate_fingerprint
    AND candidate.review_status = 'REVIEW_REQUIRED'
) AS 'mapping candidate source evidence is missing or inconsistent';

ASSERT (
  SELECT COUNT(*) = 1
  FROM (
    SELECT candidate.entity_type
    FROM panganlens_ops.source_mapping_review_candidate AS candidate
    WHERE candidate.candidate_fingerprint = @candidate_fingerprint
      AND candidate.review_status = 'REVIEW_REQUIRED'
      AND (
        (candidate.entity_type = 'commodity' AND EXISTS (
          SELECT 1
          FROM panganlens_core.commodity
          WHERE commodity_id = @canonical_id
        ))
        OR (candidate.entity_type = 'channel' AND EXISTS (
          SELECT 1
          FROM panganlens_core.market_channel
          WHERE channel_id = @canonical_id
        ))
        OR (candidate.entity_type = 'region' AND EXISTS (
          SELECT 1
          FROM panganlens_core.region
          WHERE region_id = @canonical_id
        ))
        OR (candidate.entity_type = 'market' AND EXISTS (
          SELECT 1
          FROM panganlens_core.market
          WHERE market_id = @canonical_id
        ))
      )
  )
) AS 'canonical_id does not exist for the candidate entity type';

ASSERT (
  SELECT COUNT(*) = 0
  FROM panganlens_ops.source_mapping_review_candidate AS candidate
  JOIN panganlens_ops.source_entity_mapping AS mapping
    ON mapping.source_system = candidate.source_system
   AND mapping.entity_type = candidate.entity_type
   AND COALESCE(mapping.source_id, '') = COALESCE(candidate.source_id, '')
   AND COALESCE(mapping.source_name_normalized, '') = COALESCE(candidate.source_name_normalized, '')
   AND COALESCE(mapping.source_level, '') = COALESCE(candidate.source_level, '')
   AND COALESCE(mapping.parent_source_id, '') = COALESCE(candidate.parent_source_id, '')
  WHERE candidate.candidate_fingerprint = @candidate_fingerprint
    AND candidate.review_status = 'REVIEW_REQUIRED'
    AND mapping.mapping_status = 'ACTIVE'
    AND mapping.valid_from <= @reviewed_at
    AND (mapping.valid_to IS NULL OR mapping.valid_to > @reviewed_at)
    AND mapping.mapping_version >= candidate.mapping_version
) AS 'active mapping version must be older than the reviewed candidate';

UPDATE panganlens_ops.source_entity_mapping AS mapping
SET
  mapping_status = 'SUPERSEDED',
  valid_to = @reviewed_at
WHERE mapping.mapping_status = 'ACTIVE'
  AND mapping.valid_from <= @reviewed_at
  AND (mapping.valid_to IS NULL OR mapping.valid_to > @reviewed_at)
  AND EXISTS (
    SELECT 1
    FROM panganlens_ops.source_mapping_review_candidate AS candidate
    WHERE candidate.candidate_fingerprint = @candidate_fingerprint
      AND candidate.review_status = 'REVIEW_REQUIRED'
      AND mapping.source_system = candidate.source_system
      AND mapping.entity_type = candidate.entity_type
      AND COALESCE(mapping.source_id, '') = COALESCE(candidate.source_id, '')
      AND COALESCE(mapping.source_name_normalized, '') = COALESCE(candidate.source_name_normalized, '')
      AND COALESCE(mapping.source_level, '') = COALESCE(candidate.source_level, '')
      AND COALESCE(mapping.parent_source_id, '') = COALESCE(candidate.parent_source_id, '')
  );

INSERT INTO panganlens_ops.source_entity_mapping (
  source_system,
  entity_type,
  source_id,
  source_name_normalized,
  source_level,
  parent_source_id,
  canonical_id,
  mapping_version,
  mapping_status,
  reviewed_at,
  reviewed_by,
  valid_from,
  valid_to,
  mapping_note
)
SELECT
  candidate.source_system,
  candidate.entity_type,
  candidate.source_id,
  candidate.source_name_normalized,
  candidate.source_level,
  candidate.parent_source_id,
  @canonical_id,
  candidate.mapping_version,
  'ACTIVE',
  @reviewed_at,
  @reviewed_by,
  @reviewed_at,
  NULL,
  @review_note
FROM panganlens_ops.source_mapping_review_candidate AS candidate
WHERE candidate.candidate_fingerprint = @candidate_fingerprint
  AND candidate.review_status = 'REVIEW_REQUIRED';

UPDATE panganlens_ops.source_mapping_review_candidate
SET
  review_status = 'APPROVED',
  proposed_canonical_id = @canonical_id,
  reviewed_at = @reviewed_at,
  reviewed_by = @reviewed_by,
  review_note = @review_note
WHERE candidate_fingerprint = @candidate_fingerprint
  AND review_status = 'REVIEW_REQUIRED';

ASSERT (
  SELECT COUNT(*) = 1
  FROM panganlens_ops.vw_active_source_entity_mapping AS active
  JOIN panganlens_ops.source_mapping_review_candidate AS candidate
    ON candidate.candidate_fingerprint = @candidate_fingerprint
   AND active.source_system = candidate.source_system
   AND active.entity_type = candidate.entity_type
   AND COALESCE(active.source_id, '') = COALESCE(candidate.source_id, '')
   AND COALESCE(active.source_name_normalized, '') = COALESCE(candidate.source_name_normalized, '')
   AND COALESCE(active.source_level, '') = COALESCE(candidate.source_level, '')
   AND COALESCE(active.parent_source_id, '') = COALESCE(candidate.parent_source_id, '')
  WHERE active.canonical_id = @canonical_id
    AND active.mapping_version = candidate.mapping_version
) AS 'reviewed mapping activation did not produce exactly one active row';

COMMIT TRANSACTION;

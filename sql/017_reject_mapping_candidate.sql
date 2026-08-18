BEGIN TRANSACTION;

ASSERT (
  SELECT COUNT(*) = 1
  FROM panganlens_ops.source_mapping_review_candidate
  WHERE candidate_fingerprint = @candidate_fingerprint
    AND review_status = 'REVIEW_REQUIRED'
) AS 'mapping candidate must exist exactly once and require review';

ASSERT LENGTH(TRIM(@reviewed_by)) > 0
AS 'reviewed_by must not be empty';

ASSERT @reviewed_at <= CURRENT_TIMESTAMP()
AS 'reviewed_at must not be in the future';

ASSERT LENGTH(TRIM(@review_note)) > 0
AS 'review_note must explain the rejection decision';

UPDATE panganlens_ops.source_mapping_review_candidate
SET
  review_status = 'REJECTED',
  proposed_canonical_id = NULL,
  reviewed_at = @reviewed_at,
  reviewed_by = @reviewed_by,
  review_note = @review_note
WHERE candidate_fingerprint = @candidate_fingerprint
  AND review_status = 'REVIEW_REQUIRED';

ASSERT (
  SELECT COUNT(*) = 1
  FROM panganlens_ops.source_mapping_review_candidate
  WHERE candidate_fingerprint = @candidate_fingerprint
    AND review_status = 'REJECTED'
    AND proposed_canonical_id IS NULL
    AND reviewed_at = @reviewed_at
    AND reviewed_by = @reviewed_by
    AND review_note = @review_note
) AS 'mapping rejection did not produce exactly one reviewed row';

COMMIT TRANSACTION;

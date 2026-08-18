-- Looker Studio can use this one-row view for public freshness and publish metadata.
-- The pointer advances only after a successful pipeline run.
-- Business-day age excludes Saturday and Sunday. The observation date remains visible.

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_publish_state AS
WITH active_state AS (
  SELECT
    state.state_name,
    state.active_run_id,
    state.active_observation_date,
    state.published_at,
    run.status AS active_run_status,
    run.rows_received,
    run.rows_clean,
    run.rows_duplicate,
    run.rows_conflict,
    run.rows_quarantined
  FROM panganlens_ops.publish_state AS state
  INNER JOIN panganlens_ops.pipeline_run AS run
    ON state.active_run_id = run.run_id
  WHERE state.state_name = 'public_dashboard'
    AND run.status = 'SUCCESS'
),
with_age AS (
  SELECT
    active_state.*,
    DATE(published_at, 'Asia/Jakarta') AS published_date_wib,
    (
      SELECT COUNTIF(EXTRACT(DAYOFWEEK FROM day) BETWEEN 2 AND 6)
      FROM UNNEST(GENERATE_DATE_ARRAY(
        active_observation_date,
        CURRENT_DATE('Asia/Jakarta')
      )) AS day
    ) - 1 AS observation_business_days_old
  FROM active_state
)
SELECT
  state_name,
  active_run_id,
  active_observation_date,
  published_at,
  published_date_wib,
  active_run_status,
  rows_received,
  rows_clean,
  rows_duplicate,
  rows_conflict,
  rows_quarantined,
  observation_business_days_old,
  CASE
    WHEN observation_business_days_old <= 1 THEN 'Terkini'
    WHEN observation_business_days_old <= 2 THEN 'Perlu diperiksa'
    ELSE 'Data lama'
  END AS freshness_label
FROM with_age;

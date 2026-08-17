-- Looker Studio can use this one-row view for public freshness and publish metadata.
-- The pointer advances only after a successful pipeline run.

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_publish_state AS
SELECT
  state.state_name,
  state.active_run_id,
  state.active_observation_date,
  state.published_at,
  DATE(state.published_at, 'Asia/Jakarta') AS published_date_wib,
  run.status AS active_run_status,
  run.rows_received,
  run.rows_clean,
  run.rows_duplicate,
  run.rows_conflict,
  run.rows_quarantined,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), state.published_at, HOUR) AS freshness_hours,
  CASE
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), state.published_at, HOUR) <= 36 THEN 'Terkini'
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), state.published_at, HOUR) <= 72 THEN 'Perlu diperiksa'
    ELSE 'Data lama'
  END AS freshness_label
FROM panganlens_ops.publish_state AS state
INNER JOIN panganlens_ops.pipeline_run AS run
  ON state.active_run_id = run.run_id
WHERE state.state_name = 'public_dashboard'
  AND run.status = 'SUCCESS';

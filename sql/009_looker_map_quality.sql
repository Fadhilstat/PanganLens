-- Validate the map-facing grain before publishing the Looker Studio view.
WITH duplicate_grain AS (
  SELECT
    observation_date,
    commodity_id,
    channel_id,
    province_id,
    COUNT(*) AS row_count
  FROM panganlens_mart.vw_looker_province_map
  GROUP BY observation_date, commodity_id, channel_id, province_id
  HAVING COUNT(*) > 1
),
invalid_rows AS (
  SELECT COUNT(*) AS row_count
  FROM panganlens_mart.vw_looker_province_map
  WHERE province_id IS NULL
    OR province_name IS NULL
    OR TRIM(province_name) = ''
    OR map_location IS NULL
    OR TRIM(map_location) = ''
    OR map_country_code != 'ID'
    OR price_idr <= 0
)
SELECT
  'province_map_unique_grain' AS check_name,
  COUNT(*) AS failure_count,
  IF(COUNT(*) = 0, 'PASS', 'FAIL') AS status
FROM duplicate_grain

UNION ALL

SELECT
  'province_map_required_fields',
  row_count,
  IF(row_count = 0, 'PASS', 'FAIL')
FROM invalid_rows;

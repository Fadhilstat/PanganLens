-- Looker Studio should connect to these curated views, not raw or staging tables.
-- Prices remain NUMERIC so charts, sorting, aggregation, and currency formatting stay correct.

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_national_price_daily AS
SELECT
  fact.observation_date,
  EXTRACT(YEAR FROM fact.observation_date) AS observation_year,
  EXTRACT(MONTH FROM fact.observation_date) AS observation_month,
  DATE_TRUNC(fact.observation_date, MONTH) AS observation_month_start,
  commodity.commodity_id,
  commodity.commodity_name,
  category.category_id,
  category.category_name,
  commodity.display_order AS commodity_display_order,
  unit_ref.unit_id,
  unit_ref.unit_name,
  unit_ref.unit_symbol,
  channel.channel_id,
  channel.channel_name,
  fact.price AS price_idr,
  CONCAT('Rp per ', unit_ref.unit_symbol) AS price_unit_label,
  fact.source_capture_id,
  fact.loaded_at
FROM panganlens_core.food_price_national AS fact
INNER JOIN panganlens_core.commodity AS commodity
  ON fact.commodity_id = commodity.commodity_id
INNER JOIN panganlens_core.commodity_category AS category
  ON commodity.category_id = category.category_id
INNER JOIN panganlens_core.unit AS unit_ref
  ON commodity.unit_id = unit_ref.unit_id
INNER JOIN panganlens_core.market_channel AS channel
  ON fact.channel_id = channel.channel_id;

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_region_price_daily AS
SELECT
  fact.observation_date,
  EXTRACT(YEAR FROM fact.observation_date) AS observation_year,
  EXTRACT(MONTH FROM fact.observation_date) AS observation_month,
  DATE_TRUNC(fact.observation_date, MONTH) AS observation_month_start,
  commodity.commodity_id,
  commodity.commodity_name,
  category.category_id,
  category.category_name,
  commodity.display_order AS commodity_display_order,
  unit_ref.unit_id,
  unit_ref.unit_name,
  unit_ref.unit_symbol,
  channel.channel_id,
  channel.channel_name,
  region.region_id,
  region.region_name,
  region.region_level,
  CASE region.region_level
    WHEN 'province' THEN 'Provinsi'
    WHEN 'regency' THEN 'Kabupaten/Kota'
    ELSE region.region_level
  END AS region_level_label,
  fact.price AS price_idr,
  CONCAT('Rp per ', unit_ref.unit_symbol) AS price_unit_label,
  fact.source_capture_id,
  fact.loaded_at
FROM panganlens_core.food_price_region AS fact
INNER JOIN panganlens_core.commodity AS commodity
  ON fact.commodity_id = commodity.commodity_id
INNER JOIN panganlens_core.commodity_category AS category
  ON commodity.category_id = category.category_id
INNER JOIN panganlens_core.unit AS unit_ref
  ON commodity.unit_id = unit_ref.unit_id
INNER JOIN panganlens_core.market_channel AS channel
  ON fact.channel_id = channel.channel_id
INNER JOIN panganlens_core.region AS region
  ON fact.region_id = region.region_id;

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_latest_region_price AS
SELECT * EXCEPT(row_rank)
FROM (
  SELECT
    region_daily.*,
    ROW_NUMBER() OVER (
      PARTITION BY commodity_id, channel_id, region_id
      ORDER BY observation_date DESC, loaded_at DESC
    ) AS row_rank
  FROM panganlens_mart.vw_looker_region_price_daily AS region_daily
)
WHERE row_rank = 1;

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_province_map AS
WITH latest_province AS (
  SELECT
    observation_date,
    commodity_id,
    commodity_name,
    category_id,
    category_name,
    commodity_display_order,
    unit_id,
    unit_name,
    unit_symbol,
    channel_id,
    channel_name,
    region_id,
    region_name,
    price_idr,
    price_unit_label,
    loaded_at
  FROM panganlens_mart.vw_looker_latest_region_price
  WHERE region_level = 'province'
),
benchmarked AS (
  SELECT
    latest_province.*,
    AVG(price_idr) OVER (
      PARTITION BY observation_date, commodity_id, channel_id
    ) AS province_average_price_idr
  FROM latest_province
)
SELECT
  observation_date,
  commodity_id,
  commodity_name,
  category_id,
  category_name,
  commodity_display_order,
  unit_id,
  unit_name,
  unit_symbol,
  channel_id,
  channel_name,
  region_id AS province_id,
  region_name AS province_name,
  region_name AS map_location,
  'ID' AS map_country_code,
  price_idr,
  province_average_price_idr,
  SAFE_DIVIDE(
    price_idr - province_average_price_idr,
    province_average_price_idr
  ) AS price_gap_vs_province_average_pct,
  price_unit_label,
  loaded_at
FROM benchmarked;

CREATE OR REPLACE VIEW panganlens_mart.vw_looker_pipeline_health AS
SELECT
  run_id,
  started_at,
  finished_at,
  DATE(started_at, 'Asia/Jakarta') AS run_date_wib,
  status,
  source_observation_date,
  rows_received,
  rows_clean,
  rows_duplicate,
  rows_conflict,
  rows_quarantined,
  error_message,
  CASE status
    WHEN 'SUCCESS' THEN 1
    WHEN 'NO_NEW_DATA' THEN 2
    WHEN 'BLOCKED' THEN 3
    WHEN 'FAILED' THEN 4
    ELSE 9
  END AS status_sort_key,
  CASE status
    WHEN 'SUCCESS' THEN 'Sehat'
    WHEN 'NO_NEW_DATA' THEN 'Belum ada data baru'
    WHEN 'BLOCKED' THEN 'Publikasi ditahan'
    WHEN 'FAILED' THEN 'Gagal'
    ELSE status
  END AS status_label
FROM panganlens_ops.pipeline_run;

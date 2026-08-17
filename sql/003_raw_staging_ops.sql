CREATE TABLE IF NOT EXISTS panganlens_ops.pipeline_run (
  run_id STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  status STRING NOT NULL,
  source_observation_date DATE,
  rows_received INT64 NOT NULL,
  rows_clean INT64 NOT NULL,
  rows_duplicate INT64 NOT NULL,
  rows_conflict INT64 NOT NULL,
  rows_quarantined INT64 NOT NULL,
  error_message STRING,
  PRIMARY KEY (run_id) NOT ENFORCED
)
PARTITION BY DATE(started_at);

CREATE TABLE IF NOT EXISTS panganlens_ops.source_capture (
  capture_id STRING NOT NULL,
  run_id STRING NOT NULL,
  source_name STRING NOT NULL,
  source_method STRING NOT NULL,
  source_url STRING NOT NULL,
  source_host STRING NOT NULL,
  content_type STRING,
  request_fingerprint STRING NOT NULL,
  schema_fingerprint STRING NOT NULL,
  requested_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  http_status INT64,
  payload_bytes INT64,
  payload_sha256 STRING,
  status STRING NOT NULL,
  error_message STRING,
  PRIMARY KEY (capture_id) NOT ENFORCED,
  FOREIGN KEY (run_id)
    REFERENCES panganlens_ops.pipeline_run(run_id) NOT ENFORCED
)
PARTITION BY DATE(requested_at)
CLUSTER BY run_id, source_method;

CREATE TABLE IF NOT EXISTS panganlens_raw.raw_food_price_capture (
  capture_id STRING NOT NULL,
  run_id STRING NOT NULL,
  captured_at TIMESTAMP NOT NULL,
  source_method STRING NOT NULL,
  request_parameters JSON,
  request_fingerprint STRING NOT NULL,
  schema_fingerprint STRING NOT NULL,
  payload_text STRING NOT NULL,
  payload_bytes INT64 NOT NULL,
  payload_sha256 STRING NOT NULL
)
PARTITION BY DATE(captured_at)
CLUSTER BY run_id, capture_id;

CREATE TABLE IF NOT EXISTS panganlens_staging.normalized_price_candidate (
  run_id STRING NOT NULL,
  capture_id STRING NOT NULL,
  observation_date DATE NOT NULL,
  scope STRING NOT NULL,
  commodity_id STRING,
  channel_id STRING,
  region_id STRING,
  market_id STRING,
  source_row_name STRING NOT NULL,
  source_row_level STRING NOT NULL,
  source_row_no STRING NOT NULL,
  price NUMERIC NOT NULL,
  source_method STRING NOT NULL,
  mapping_status STRING NOT NULL,
  mapping_version INT64,
  mapping_key_fingerprint STRING,
  validation_status STRING NOT NULL,
  quarantine_reason STRING,
  business_key_hash STRING,
  record_hash STRING,
  normalized_at TIMESTAMP NOT NULL
)
PARTITION BY observation_date
CLUSTER BY run_id, mapping_status, validation_status;

CREATE TABLE IF NOT EXISTS panganlens_ops.data_quality_result (
  run_id STRING NOT NULL,
  check_name STRING NOT NULL,
  check_scope STRING NOT NULL,
  severity STRING NOT NULL,
  status STRING NOT NULL,
  affected_rows INT64 NOT NULL,
  details JSON,
  checked_at TIMESTAMP NOT NULL,
  PRIMARY KEY (run_id, check_name, check_scope) NOT ENFORCED,
  FOREIGN KEY (run_id)
    REFERENCES panganlens_ops.pipeline_run(run_id) NOT ENFORCED
)
PARTITION BY DATE(checked_at);

CREATE TABLE IF NOT EXISTS panganlens_ops.duplicate_log (
  run_id STRING NOT NULL,
  business_key_hash STRING NOT NULL,
  record_hash STRING NOT NULL,
  kept_capture_id STRING NOT NULL,
  duplicate_capture_id STRING NOT NULL,
  detected_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(detected_at)
CLUSTER BY business_key_hash;

CREATE TABLE IF NOT EXISTS panganlens_ops.conflict_log (
  conflict_id STRING NOT NULL,
  run_id STRING NOT NULL,
  business_key_hash STRING NOT NULL,
  conflicting_record_hashes ARRAY<STRING> NOT NULL,
  conflict_payload JSON NOT NULL,
  resolution_status STRING NOT NULL,
  detected_at TIMESTAMP NOT NULL,
  resolved_at TIMESTAMP,
  resolution_note STRING,
  PRIMARY KEY (conflict_id) NOT ENFORCED
)
PARTITION BY DATE(detected_at)
CLUSTER BY business_key_hash, resolution_status;

CREATE TABLE IF NOT EXISTS panganlens_ops.revision_history (
  revision_id STRING NOT NULL,
  business_key_hash STRING NOT NULL,
  old_record_hash STRING NOT NULL,
  new_record_hash STRING NOT NULL,
  old_price NUMERIC NOT NULL,
  new_price NUMERIC NOT NULL,
  old_capture_id STRING NOT NULL,
  new_capture_id STRING NOT NULL,
  detected_at TIMESTAMP NOT NULL,
  resolution_status STRING NOT NULL,
  resolution_note STRING,
  PRIMARY KEY (revision_id) NOT ENFORCED
)
PARTITION BY DATE(detected_at)
CLUSTER BY business_key_hash, resolution_status;

CREATE TABLE IF NOT EXISTS panganlens_core.commodity_category (
  category_id STRING NOT NULL,
  category_name STRING NOT NULL,
  source_category_code STRING,
  is_active BOOL NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (category_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS panganlens_core.unit (
  unit_id STRING NOT NULL,
  unit_name STRING NOT NULL,
  unit_symbol STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (unit_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS panganlens_core.market_channel (
  channel_id STRING NOT NULL,
  channel_name STRING NOT NULL,
  source_price_type_id STRING,
  is_active BOOL NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (channel_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS panganlens_core.commodity (
  commodity_id STRING NOT NULL,
  category_id STRING NOT NULL,
  unit_id STRING NOT NULL,
  commodity_name STRING NOT NULL,
  source_commodity_code STRING,
  is_active BOOL NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (commodity_id) NOT ENFORCED,
  FOREIGN KEY (category_id)
    REFERENCES panganlens_core.commodity_category(category_id) NOT ENFORCED,
  FOREIGN KEY (unit_id)
    REFERENCES panganlens_core.unit(unit_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS panganlens_core.region (
  region_id STRING NOT NULL,
  parent_region_id STRING,
  region_level STRING NOT NULL,
  official_code STRING,
  source_region_code STRING,
  region_name STRING NOT NULL,
  is_active BOOL NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (region_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS panganlens_core.market (
  market_id STRING NOT NULL,
  region_id STRING NOT NULL,
  channel_id STRING NOT NULL,
  market_name STRING NOT NULL,
  source_market_code STRING,
  is_active BOOL NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (market_id) NOT ENFORCED,
  FOREIGN KEY (region_id)
    REFERENCES panganlens_core.region(region_id) NOT ENFORCED,
  FOREIGN KEY (channel_id)
    REFERENCES panganlens_core.market_channel(channel_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS panganlens_core.food_price_national (
  observation_date DATE NOT NULL,
  commodity_id STRING NOT NULL,
  channel_id STRING NOT NULL,
  price NUMERIC NOT NULL,
  source_capture_id STRING NOT NULL,
  record_hash STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (observation_date, commodity_id, channel_id) NOT ENFORCED,
  FOREIGN KEY (commodity_id)
    REFERENCES panganlens_core.commodity(commodity_id) NOT ENFORCED,
  FOREIGN KEY (channel_id)
    REFERENCES panganlens_core.market_channel(channel_id) NOT ENFORCED
)
PARTITION BY observation_date
CLUSTER BY commodity_id, channel_id;

CREATE TABLE IF NOT EXISTS panganlens_core.food_price_region (
  observation_date DATE NOT NULL,
  commodity_id STRING NOT NULL,
  channel_id STRING NOT NULL,
  region_id STRING NOT NULL,
  price NUMERIC NOT NULL,
  source_capture_id STRING NOT NULL,
  record_hash STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (observation_date, commodity_id, channel_id, region_id) NOT ENFORCED,
  FOREIGN KEY (commodity_id)
    REFERENCES panganlens_core.commodity(commodity_id) NOT ENFORCED,
  FOREIGN KEY (channel_id)
    REFERENCES panganlens_core.market_channel(channel_id) NOT ENFORCED,
  FOREIGN KEY (region_id)
    REFERENCES panganlens_core.region(region_id) NOT ENFORCED
)
PARTITION BY observation_date
CLUSTER BY commodity_id, region_id, channel_id;

CREATE TABLE IF NOT EXISTS panganlens_core.food_price_market (
  observation_date DATE NOT NULL,
  commodity_id STRING NOT NULL,
  market_id STRING NOT NULL,
  price NUMERIC NOT NULL,
  source_capture_id STRING NOT NULL,
  record_hash STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (observation_date, commodity_id, market_id) NOT ENFORCED,
  FOREIGN KEY (commodity_id)
    REFERENCES panganlens_core.commodity(commodity_id) NOT ENFORCED,
  FOREIGN KEY (market_id)
    REFERENCES panganlens_core.market(market_id) NOT ENFORCED
)
PARTITION BY observation_date
CLUSTER BY commodity_id, market_id;

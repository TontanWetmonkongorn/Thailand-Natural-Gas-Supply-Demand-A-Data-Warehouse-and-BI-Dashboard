CREATE TABLE IF NOT EXISTS dim_month (
    month_start DATE PRIMARY KEY CHECK (day(month_start) = 1),
    calendar_year SMALLINT NOT NULL CHECK (calendar_year = year(month_start)),
    month_number SMALLINT NOT NULL CHECK (month_number = month(month_start)),
    month_name VARCHAR NOT NULL CHECK (month_name = strftime(month_start, '%B')),
    days_in_month SMALLINT NOT NULL CHECK (days_in_month = day(last_day(month_start))),
    UNIQUE (calendar_year, month_number)
);

CREATE TABLE IF NOT EXISTS dim_unit (
    unit_code VARCHAR PRIMARY KEY,
    unit_name VARCHAR NOT NULL,
    measure_kind VARCHAR NOT NULL CHECK (measure_kind IN ('RATE', 'PERCENTAGE'))
);

CREATE SEQUENCE IF NOT EXISTS gas_source_key_seq START 1;
CREATE TABLE IF NOT EXISTS dim_gas_source (
    gas_source_key BIGINT PRIMARY KEY DEFAULT nextval('gas_source_key_seq'),
    source_code VARCHAR NOT NULL,
    definition_version_id BIGINT NOT NULL REFERENCES meta_definition_version(definition_version_id),
    source_name VARCHAR NOT NULL,
    supply_group VARCHAR NOT NULL CHECK (supply_group IN ('DOMESTIC_EPPO', 'MYANMAR_IMPORT', 'LNG_IMPORT')),
    qualification_note VARCHAR,
    UNIQUE (source_code, definition_version_id)
);

CREATE SEQUENCE IF NOT EXISTS import_category_key_seq START 1;
CREATE TABLE IF NOT EXISTS dim_import_category (
    import_category_key BIGINT PRIMARY KEY DEFAULT nextval('import_category_key_seq'),
    category_code VARCHAR NOT NULL,
    definition_version_id BIGINT NOT NULL REFERENCES meta_definition_version(definition_version_id),
    category_name VARCHAR NOT NULL,
    denominator_description VARCHAR NOT NULL,
    UNIQUE (category_code, definition_version_id)
);

CREATE SEQUENCE IF NOT EXISTS resource_id_seq START 1;
CREATE TABLE IF NOT EXISTS meta_resource (
    resource_id BIGINT PRIMARY KEY DEFAULT nextval('resource_id_seq'),
    resource_code VARCHAR NOT NULL UNIQUE,
    publisher_name VARCHAR NOT NULL,
    publisher_resource_id VARCHAR NOT NULL,
    download_url VARCHAR NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS snapshot_id_seq START 1;
CREATE TABLE IF NOT EXISTS meta_snapshot (
    snapshot_id BIGINT PRIMARY KEY DEFAULT nextval('snapshot_id_seq'),
    resource_id BIGINT NOT NULL REFERENCES meta_resource(resource_id),
    sha256 VARCHAR NOT NULL,
    raw_path VARCHAR NOT NULL,
    download_url_at_retrieval VARCHAR NOT NULL,
    retrieved_at TIMESTAMPTZ,
    UNIQUE (resource_id, sha256)
);

CREATE SEQUENCE IF NOT EXISTS load_id_seq START 1;
CREATE TABLE IF NOT EXISTS meta_load (
    load_id BIGINT PRIMARY KEY DEFAULT nextval('load_id_seq'),
    snapshot_id BIGINT NOT NULL REFERENCES meta_snapshot(snapshot_id),
    definition_version_id BIGINT NOT NULL REFERENCES meta_definition_version(definition_version_id),
    transform_version VARCHAR NOT NULL,
    ruleset_version VARCHAR NOT NULL,
    resolution_manifest_sha256 VARCHAR NOT NULL,
    parquet_sha256 VARCHAR NOT NULL,
    load_state VARCHAR NOT NULL CHECK (load_state = 'COMPLETE'),
    UNIQUE (snapshot_id, definition_version_id, transform_version, ruleset_version, resolution_manifest_sha256)
);

CREATE TABLE IF NOT EXISTS meta_quality_run (
    load_id BIGINT PRIMARY KEY REFERENCES meta_load(load_id),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    evidence JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_gas_supply_monthly (
    load_id BIGINT REFERENCES meta_load(load_id),
    month_start DATE REFERENCES dim_month(month_start),
    gas_source_key BIGINT REFERENCES dim_gas_source(gas_source_key),
    unit_code VARCHAR NOT NULL REFERENCES dim_unit(unit_code) CHECK (unit_code = 'MMSCFD'),
    source_record_number BIGINT NOT NULL CHECK (source_record_number > 0),
    supply_rate_mmscfd DECIMAL(18,6) NOT NULL CHECK (supply_rate_mmscfd >= 0),
    PRIMARY KEY (load_id, month_start, gas_source_key),
    UNIQUE (load_id, source_record_number)
);

CREATE TABLE IF NOT EXISTS fact_gas_consumption_monthly (
    load_id BIGINT REFERENCES meta_load(load_id),
    month_start DATE REFERENCES dim_month(month_start),
    sector_key BIGINT REFERENCES dim_sector(sector_key),
    unit_code VARCHAR NOT NULL REFERENCES dim_unit(unit_code) CHECK (unit_code = 'MMSCFD'),
    source_record_number BIGINT NOT NULL CHECK (source_record_number > 0),
    consumption_rate_mmscfd DECIMAL(18,6) NOT NULL CHECK (consumption_rate_mmscfd >= 0),
    PRIMARY KEY (load_id, month_start, sector_key),
    UNIQUE (load_id, source_record_number)
);

CREATE TABLE IF NOT EXISTS fact_import_share_monthly (
    load_id BIGINT REFERENCES meta_load(load_id),
    month_start DATE REFERENCES dim_month(month_start),
    import_category_key BIGINT REFERENCES dim_import_category(import_category_key),
    unit_code VARCHAR NOT NULL REFERENCES dim_unit(unit_code) CHECK (unit_code = '%'),
    source_record_number BIGINT NOT NULL CHECK (source_record_number > 0),
    import_share_pct DECIMAL(18,6) NOT NULL CHECK (import_share_pct >= 0 AND import_share_pct <= 100),
    PRIMARY KEY (load_id, month_start, import_category_key),
    UNIQUE (load_id, source_record_number)
);

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS meta_definition_version (
    definition_version_id BIGINT PRIMARY KEY,
    version_label VARCHAR NOT NULL UNIQUE,
    manifest_path VARCHAR NOT NULL,
    manifest_sha256 VARCHAR NOT NULL,
    evidence_references VARCHAR NOT NULL,
    review_state VARCHAR NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS sector_key_seq START 1;

CREATE TABLE IF NOT EXISTS dim_sector (
    sector_key BIGINT PRIMARY KEY DEFAULT nextval('sector_key_seq'),
    sector_code VARCHAR NOT NULL,
    definition_version_id BIGINT NOT NULL
        REFERENCES meta_definition_version (definition_version_id),
    sector_name VARCHAR NOT NULL,
    definition_note VARCHAR,
    UNIQUE (sector_code, definition_version_id)
);

COMMIT;

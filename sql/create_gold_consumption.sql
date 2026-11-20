CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.monthly_sector_consumption AS
SELECT
    f.month_start,
    d.sector_code,
    d.sector_name,
    f.consumption_rate_mmscfd,
    f.unit_code,
    f.load_id
FROM fact_gas_consumption_monthly AS f
JOIN meta_load AS l ON l.load_id = f.load_id
JOIN dim_sector AS d
    ON d.sector_key = f.sector_key
    AND d.definition_version_id = l.definition_version_id
WHERE f.load_id = {load_id}
  AND f.month_start >= DATE '2015-01-01'
  AND f.month_start < DATE '2026-01-01';

CREATE OR REPLACE VIEW gold.monthly_consumption_totals AS
SELECT
    load_id,
    month_start,
    unit_code,
    COUNT(*) AS sector_row_count,
    COUNT(*) = 4
        AND COUNT(DISTINCT sector_code) = 4
        AND COUNT(*) FILTER (
            WHERE sector_code IN ('ELECTRICITY', 'GSP', 'INDUSTRY', 'NGV')
        ) = 4 AS sectors_complete,
    CASE WHEN sectors_complete THEN SUM(consumption_rate_mmscfd) END
        AS reported_consumption_mmscfd
FROM gold.monthly_sector_consumption
GROUP BY load_id, month_start, unit_code;

CREATE OR REPLACE VIEW gold.monthly_consumption_sector_shares AS
SELECT
    s.load_id,
    s.month_start,
    s.sector_code,
    s.sector_name,
    s.consumption_rate_mmscfd,
    t.reported_consumption_mmscfd,
    t.sectors_complete,
    100.0 * s.consumption_rate_mmscfd
        / NULLIF(t.reported_consumption_mmscfd, 0) AS sector_share_pct
FROM gold.monthly_sector_consumption AS s
JOIN gold.monthly_consumption_totals AS t USING (load_id, month_start, unit_code);

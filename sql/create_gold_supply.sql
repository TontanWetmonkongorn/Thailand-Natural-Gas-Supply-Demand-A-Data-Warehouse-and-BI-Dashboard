CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.monthly_supply_by_source AS
WITH comparison AS (
    SELECT
        q.load_id,
        try_cast(json_extract_string(m.value, '$.month') || '-01' AS DATE) AS month_start,
        json_extract_string(m.value, '$.status') AS import_mix_status
    FROM meta_quality_run AS q,
        json_each(q.evidence, '$.silver_manifest.import_mix_comparison.months') AS m
    WHERE q.load_id = {load_id}
)
SELECT
    f.load_id,
    f.month_start,
    d.source_code,
    d.source_name,
    d.supply_group,
    d.qualification_note,
    f.supply_rate_mmscfd,
    f.unit_code,
    'UNRESOLVED' AS source_completeness,
    coalesce(c.import_mix_status, 'NOT_CHECKED') AS import_mix_status
FROM fact_gas_supply_monthly AS f
JOIN meta_load AS l ON l.load_id = f.load_id
JOIN dim_gas_source AS d
    ON d.gas_source_key = f.gas_source_key
    AND d.definition_version_id = l.definition_version_id
LEFT JOIN comparison AS c
    ON c.load_id = f.load_id AND c.month_start = f.month_start
WHERE f.load_id = {load_id}
  AND f.month_start >= DATE '2015-01-01'
  AND f.month_start < DATE '2026-01-01';

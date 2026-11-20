CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.monthly_published_import_mix AS
SELECT
    f.load_id,
    f.month_start,
    d.category_code,
    d.category_name,
    d.denominator_description,
    f.import_share_pct,
    f.unit_code
FROM fact_import_share_monthly AS f
JOIN meta_load AS l ON l.load_id = f.load_id
JOIN dim_import_category AS d
    ON d.import_category_key = f.import_category_key
    AND d.definition_version_id = l.definition_version_id
WHERE f.load_id = {load_id}
  AND f.month_start >= DATE '2015-01-01'
  AND f.month_start < DATE '2026-01-01';

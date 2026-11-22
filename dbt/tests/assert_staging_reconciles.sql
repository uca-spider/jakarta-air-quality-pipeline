-- Fails (returns a row) when raw rows are not fully accounted for:
-- every row in aq_raw.ispu must be either in stg_ispu or in stg_ispu_rejects.
WITH counts AS (
    SELECT
        (SELECT COUNT(*) FROM {{ source('aq_raw', 'ispu') }}) AS raw_rows,
        (SELECT COUNT(*) FROM {{ ref('stg_ispu') }})          AS stg_rows,
        (SELECT COUNT(*) FROM {{ ref('stg_ispu_rejects') }})  AS reject_rows
)
SELECT *
FROM counts
WHERE raw_rows != stg_rows + reject_rows

/*
    Every raw row that does NOT reach stg_ispu, with the reason.
    Invariant (enforced by tests/assert_staging_reconciles.sql):
        count(aq_raw.ispu) = count(stg_ispu) + count(stg_ispu_rejects)

    The key logic mirrors stg_ispu.sql. Keep both in sync.
*/
WITH typed AS (
    SELECT
        SAFE.PARSE_DATE('%Y-%m-%d', tanggal) AS measurement_date,
        REGEXP_EXTRACT(UPPER(TRIM(stasiun)), r'^(DKI[1-5])') AS station_id,
        tanggal,
        stasiun,
        source_file,
        file_hash,
        SAFE_CAST(loaded_at AS TIMESTAMP) AS ingested_at
    FROM {{ source('aq_raw', 'ispu') }}
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY measurement_date, station_id
            -- Overlap rule: the file published for the same year as the date wins
            -- (only December 2022 overlaps: 2022 file vs 2023 file). Then newest load.
            ORDER BY
                IF(REGEXP_EXTRACT(source_file, r'(20\d{2})')
                     = CAST(EXTRACT(YEAR FROM measurement_date) AS STRING), 0, 1),
                ingested_at DESC,
                source_file DESC
        ) AS rn
    FROM typed
    WHERE measurement_date IS NOT NULL
      AND station_id IS NOT NULL
)

SELECT tanggal, stasiun, source_file, file_hash, ingested_at,
       'UNPARSEABLE_DATE' AS reject_reason
FROM typed
WHERE measurement_date IS NULL

UNION ALL

SELECT tanggal, stasiun, source_file, file_hash, ingested_at,
       'UNKNOWN_STATION' AS reject_reason
FROM typed
WHERE measurement_date IS NOT NULL AND station_id IS NULL

UNION ALL

SELECT tanggal, stasiun, source_file, file_hash, ingested_at,
       'OVERLAP_ACROSS_FILES' AS reject_reason
FROM ranked
WHERE rn > 1

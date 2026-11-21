WITH source AS (
    SELECT * FROM {{ source('aq_raw', 'ispu') }}
),

renamed_and_cast AS (
    SELECT
        -- Surrogate Primary Key matching the grain: (measurement_date, station_id)
        TO_HEX(
            MD5(
                CONCAT(
                    COALESCE(tanggal, ''),
                    '_',
                    COALESCE(REGEXP_EXTRACT(UPPER(TRIM(stasiun)), r'^(DKI[1-5])'), 'UNKNOWN')
                )
            )
        ) AS ispu_id,

        -- Date & Period
        SAFE.PARSE_DATE('%Y-%m-%d', tanggal) AS measurement_date,
        TRIM(periode_data) AS periode_data,

        -- Station Identification
        REGEXP_EXTRACT(UPPER(TRIM(stasiun)), r'^(DKI[1-5])') AS station_id,
        TRIM(stasiun) AS station_name_raw,

        -- Pollutant Measurements (SAFE_CAST turns invalid markers like '---' or '' into NULL)
        SAFE_CAST(pm10 AS FLOAT64) AS pm10,
        SAFE_CAST(pm25 AS FLOAT64) AS pm25,
        SAFE_CAST(so2 AS FLOAT64) AS so2,
        SAFE_CAST(co AS FLOAT64) AS co,
        SAFE_CAST(o3 AS FLOAT64) AS o3,
        SAFE_CAST(no2 AS FLOAT64) AS no2,
        SAFE_CAST(max AS FLOAT64) AS max_ispu,

        -- Critical Pollutant & Category
        CASE 
            WHEN UPPER(TRIM(critical)) IN ('', '---', 'N/A', 'NULL') THEN NULL 
            ELSE UPPER(TRIM(critical)) 
        END AS critical_pollutant,
        CASE 
            WHEN UPPER(TRIM(kategori)) IN ('', '---', 'N/A', 'NULL') THEN NULL 
            ELSE UPPER(TRIM(kategori)) 
        END AS category,

        -- Lineage & Ingestion Metadata
        source_file,
        file_hash,
        SAFE_CAST(loaded_at AS TIMESTAMP) AS ingested_at

    FROM source
),

final AS (
    SELECT *
    FROM renamed_and_cast
    WHERE measurement_date IS NOT NULL
      AND station_id IS NOT NULL
    -- Deduplication: keep the latest loaded record per (measurement_date, station_id)
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY measurement_date, station_id 
        ORDER BY ingested_at DESC, source_file DESC
    ) = 1
)

SELECT * FROM final

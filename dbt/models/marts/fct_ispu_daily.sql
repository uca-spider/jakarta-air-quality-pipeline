{{
    config(
        materialized='table',
        schema='aq_marts',
        partition_by={
            "field": "measurement_date",
            "data_type": "date",
            "granularity": "month"
        },
        cluster_by=["station_id", "category"]
    )
}}

/*
    Fact table: Daily Air Quality Index measurements per station.
    Grain: 1 row per station (station_id) per calendar day (measurement_date).
    Partitioned monthly on measurement_date and clustered on station_id, category.
*/

WITH stg AS (
    SELECT * FROM {{ ref('stg_ispu') }}
),

stations AS (
    SELECT * FROM {{ ref('dim_stations') }}
)

SELECT
    -- Keys
    s.ispu_id,
    s.measurement_date,
    s.station_id,
    
    -- Station Dimension Attributes
    st.station_name,
    st.administrative_area,
    st.latitude,
    st.longitude,

    -- Calendar Dimensions
    EXTRACT(YEAR FROM s.measurement_date) AS measurement_year,
    EXTRACT(MONTH FROM s.measurement_date) AS measurement_month,
    FORMAT_DATE('%B', s.measurement_date) AS month_name,
    FORMAT_DATE('%A', s.measurement_date) AS day_name,
    EXTRACT(DAYOFWEEK FROM s.measurement_date) IN (1, 7) AS is_weekend,

    -- Measurements
    s.pm10,
    s.pm25,
    s.so2,
    s.co,
    s.o3,
    s.no2,
    s.max_ispu,

    -- Critical Pollutant & Quality Categories
    s.critical_pollutant,
    s.category,

    -- Analytics Indicators
    s.category = 'BAIK' AS is_good_quality_day,
    s.category = 'SEDANG' AS is_moderate_quality_day,
    s.category IN ('TIDAK SEHAT', 'SANGAT TIDAK SEHAT', 'BERBAHAYA') AS is_unhealthy_day,
    s.pm25 IS NOT NULL AS has_pm25_data,

    -- Lineage metadata
    s.source_file,
    s.ingested_at

FROM stg s
LEFT JOIN stations st
    ON s.station_id = st.station_id

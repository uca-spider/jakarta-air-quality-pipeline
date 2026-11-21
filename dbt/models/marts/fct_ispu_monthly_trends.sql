{{
    config(
        materialized='table',
        schema='aq_marts',
        cluster_by=["station_id", "year"]
    )
}}

/*
    Analytics Mart: Monthly Air Quality Aggregation per Station.
    Grain: 1 row per station (station_id) per year-month.
*/

WITH daily_facts AS (
    SELECT * FROM {{ ref('fct_ispu_daily') }}
)

SELECT
    -- Grain
    CONCAT(station_id, '_', CAST(measurement_year AS STRING), '_', LPAD(CAST(measurement_month AS STRING), 2, '0')) AS monthly_trend_id,
    station_id,
    station_name,
    administrative_area,
    measurement_year AS year,
    measurement_month AS month,
    month_name,

    -- Coverage Metrics
    COUNT(1) AS total_recorded_days,
    COUNTIF(has_pm25_data) AS days_with_pm25,

    -- Pollution Indices Averages
    ROUND(AVG(max_ispu), 2) AS avg_max_ispu,
    MAX(max_ispu) AS peak_max_ispu,
    ROUND(AVG(pm10), 2) AS avg_pm10,
    ROUND(AVG(pm25), 2) AS avg_pm25,

    -- Health Quality Day Counts
    COUNTIF(is_good_quality_day) AS good_days_count,
    COUNTIF(is_moderate_quality_day) AS moderate_days_count,
    COUNTIF(is_unhealthy_day) AS unhealthy_days_count,

    -- Unhealthy Ratio Percentage
    ROUND(
        IEEE_DIVIDE(COUNTIF(is_unhealthy_day), COUNT(1)) * 100, 
        2
    ) AS pct_unhealthy_days

FROM daily_facts
GROUP BY
    station_id,
    station_name,
    administrative_area,
    year,
    month,
    month_name

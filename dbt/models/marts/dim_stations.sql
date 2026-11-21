{{
    config(
        materialized='table',
        schema='aq_marts'
    )
}}

/*
    Dimension table: Official Air Quality Monitoring Stations (SPKU) in DKI Jakarta.
    Grain: 1 row per monitoring station (station_id).
*/

WITH stations_metadata AS (
    SELECT 'DKI1' AS station_id, 'Bunderan HI' AS station_name, 'Jakarta Pusat' AS administrative_area, -6.1950 AS latitude, 106.8230 AS longitude UNION ALL
    SELECT 'DKI2' AS station_id, 'Kelapa Gading' AS station_name, 'Jakarta Utara' AS administrative_area, -6.1557 AS latitude, 106.9080 AS longitude UNION ALL
    SELECT 'DKI3' AS station_id, 'Jagakarsa' AS station_name, 'Jakarta Selatan' AS administrative_area, -6.3315 AS latitude, 106.8190 AS longitude UNION ALL
    SELECT 'DKI4' AS station_id, 'Lubang Buaya' AS station_name, 'Jakarta Timur' AS administrative_area, -6.2891 AS latitude, 106.9010 AS longitude UNION ALL
    SELECT 'DKI5' AS station_id, 'Kebon Jeruk' AS station_name, 'Jakarta Barat' AS administrative_area, -6.1904 AS latitude, 106.7670 AS longitude
)

SELECT
    station_id,
    station_name,
    CONCAT(station_id, ' - ', station_name) AS station_label,
    administrative_area,
    latitude,
    longitude
FROM stations_metadata

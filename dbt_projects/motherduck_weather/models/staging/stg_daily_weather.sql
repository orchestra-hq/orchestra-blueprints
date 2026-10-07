select
    md5(city || '|' || cast(date as varchar)) as weather_id,
    city,
    latitude,
    longitude,
    date as weather_date,
    temperature_2m_max as temp_max_c,
    temperature_2m_min as temp_min_c,
    (temperature_2m_max + temperature_2m_min) / 2 as temp_avg_c,
    coalesce(precipitation_sum, 0) as precipitation_mm,
    wind_speed_10m_max as wind_speed_max_kmh,
    _loaded_at
from {{ source('raw_weather', 'daily_weather') }}
where temperature_2m_max is not null

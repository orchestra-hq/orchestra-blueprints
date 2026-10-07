select
    city,
    min(weather_date) as first_date,
    max(weather_date) as last_date,
    count(*) as days_observed,
    round(avg(temp_avg_c), 2) as avg_temp_c,
    max(temp_max_c) as hottest_temp_c,
    min(temp_min_c) as coldest_temp_c,
    round(sum(precipitation_mm), 2) as total_precipitation_mm,
    count(*) filter (where precipitation_mm > 1) as rainy_days,
    max(wind_speed_max_kmh) as max_wind_speed_kmh
from {{ ref('stg_daily_weather') }}
group by city

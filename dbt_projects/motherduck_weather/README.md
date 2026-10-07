# MotherDuck weather dbt project

dbt-duckdb project used by `orchestra/python_duckdb_dbt_powerbi.yml`.

1. `python/duckdb_weather/ingest_weather.py` loads daily weather for five cities from Open-Meteo into `my_db.raw_weather.daily_weather`.
2. This project builds `stg_daily_weather` (view) and `city_weather_summary` (table) and tests them.
3. Orchestra refreshes the Power BI dataset afterwards.

Local run: copy `profiles.yml.example` into `~/.dbt/profiles.yml`, set `MOTHERDUCK_TOKEN`, then `pip install -r requirements.txt && dbt build`.

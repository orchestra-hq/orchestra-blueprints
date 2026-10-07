"""Load daily weather from the Open-Meteo API (no key required) into MotherDuck.

Environment variables consumed:
    MOTHERDUCK_API_TOKEN   MotherDuck service token (alias of MOTHERDUCK_TOKEN).
    WEATHER_MD_DATABASE    Target MotherDuck database (default ``my_db``).
    WEATHER_MD_SCHEMA      Target schema (default ``raw_weather``).
    WEATHER_PAST_DAYS      Days of history to fetch (default 30).
    DUCKDB_PATH            Optional local DuckDB file to use instead of MotherDuck
                           (name it ``<WEATHER_MD_DATABASE>.duckdb`` for dbt to resolve it).
"""

import os

import duckdb
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CITIES = {
    "London": (51.5072, -0.1276),
    "New York": (40.7128, -74.0060),
    "Berlin": (52.5200, 13.4050),
    "Singapore": (1.3521, 103.8198),
    "Sydney": (-33.8688, 151.2093),
}

DAILY_FIELDS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
]


def make_session() -> requests.Session:
    retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_city(
    session: requests.Session, city: str, lat: float, lon: float, past_days: int
) -> list[tuple]:
    resp = session.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(DAILY_FIELDS),
            "past_days": past_days,
            "forecast_days": 1,
            "timezone": "UTC",
        },
        timeout=30,
    )
    resp.raise_for_status()
    daily = resp.json()["daily"]
    return [
        (city, lat, lon, day, *(daily[f][i] for f in DAILY_FIELDS))
        for i, day in enumerate(daily["time"])
    ]


def main() -> None:
    database = os.environ.get("WEATHER_MD_DATABASE", "my_db")
    schema = os.environ.get("WEATHER_MD_SCHEMA", "raw_weather")
    past_days = int(os.environ.get("WEATHER_PAST_DAYS", "30"))

    session = make_session()
    rows = []
    for city, (lat, lon) in CITIES.items():
        rows.extend(fetch_city(session, city, lat, lon, past_days))
    print(f"Fetched {len(rows)} rows for {len(CITIES)} cities")

    local_path = os.environ.get("DUCKDB_PATH")
    if local_path:
        con = duckdb.connect(local_path)
    else:
        token = os.environ.get("MOTHERDUCK_API_TOKEN") or os.environ.get("MOTHERDUCK_TOKEN")
        if not token:
            raise EnvironmentError("MOTHERDUCK_API_TOKEN (or MOTHERDUCK_TOKEN) must be set.")
        con = duckdb.connect(f"md:{database}?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {schema}.daily_weather (
            city VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            date DATE,
            temperature_2m_max DOUBLE,
            temperature_2m_min DOUBLE,
            precipitation_sum DOUBLE,
            wind_speed_10m_max DOUBLE,
            _loaded_at TIMESTAMP DEFAULT current_timestamp
        )
        """
    )
    con.executemany(
        f"""
        INSERT INTO {schema}.daily_weather
            (city, latitude, longitude, date, temperature_2m_max,
             temperature_2m_min, precipitation_sum, wind_speed_10m_max)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    count = con.execute(f"SELECT count(*) FROM {schema}.daily_weather").fetchone()[0]
    print(f"Loaded {count} rows into {database}.{schema}.daily_weather")
    con.close()


if __name__ == "__main__":
    main()

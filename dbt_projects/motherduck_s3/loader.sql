-- DuckDB SQL to load S3 CSV files into MotherDuck
--
-- Prerequisites:
-- 1) You have a MotherDuck token. Replace the placeholder below.
-- 2) Your AWS credentials and S3 permissions are set up for the DuckDB process
--    (via environment variables, instance profile, or local credentials).
-- 3) Update the s3 path and (optionally) region below.

INSTALL httpfs;
LOAD httpfs;

INSTALL motherduck;
LOAD motherduck;

-- Attach MotherDuck and create a raw schema (idempotent)
ATTACH 'md:my_db' AS md (READ_ONLY FALSE);
CREATE SCHEMA IF NOT EXISTS md.raw;

-- Create or replace the raw.events table in MotherDuck from the CSV files
CREATE OR REPLACE TABLE md.raw.events AS
SELECT
	CAST(event_name AS VARCHAR) AS event_name,
	CAST(time AS TIMESTAMP) AS time,
	CAST("Name" AS VARCHAR) AS "Name",
	CAST("Number" AS BIGINT) AS "Number"
FROM read_csv_auto('s3://orchestra-sensor/event_data/sign_ins/2025_03_01/*.csv', HEADER=TRUE);

-- Preview
SELECT * FROM md.raw.events LIMIT 50;


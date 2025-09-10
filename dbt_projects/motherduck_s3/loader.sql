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

-- Authenticate to MotherDuck
-- Replace with your token or set this prior to execution via your own mechanism
SET motherduck_token='REPLACE_WITH_YOUR_MOTHERDUCK_TOKEN';

-- S3 configuration (update region if needed)
SET s3_region='us-east-1';
SET s3_url_style='path';

-- Attach MotherDuck and create a raw schema (idempotent)
ATTACH 'md:' AS md (READ_ONLY FALSE);
CREATE SCHEMA IF NOT EXISTS md.raw;

-- Set your S3 path to the folder containing the CSV files (do not remove the trailing slash)
-- Example: s3://my-bucket/events/
SET s3_events_path='s3://YOUR_BUCKET/YOUR_PREFIX/';

-- Create or replace the raw.events table in MotherDuck from the CSV files
CREATE OR REPLACE TABLE md.raw.events AS
SELECT
	CAST(event_name AS VARCHAR) AS event_name,
	CAST(time AS TIMESTAMP) AS time,
	CAST("Name" AS VARCHAR) AS "Name",
	CAST("Number" AS BIGINT) AS "Number"
FROM read_csv_auto(CONCAT(getvariable('s3_events_path'), '*.csv'), HEADER=TRUE);

-- Preview
SELECT * FROM md.raw.events LIMIT 50;


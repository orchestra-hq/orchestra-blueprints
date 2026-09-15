-- Exists only to create a ref edge to `samples_uc.trips` (Databricks' built-in
-- `samples` catalog, delivered via Delta Sharing), so it stays in scope for
-- source-freshness collection rather than being scoped out like `crm`.
select
    tpep_pickup_datetime,
    tpep_dropoff_datetime,
    trip_distance,
    fare_amount
from {{ source('samples_uc', 'trips') }}

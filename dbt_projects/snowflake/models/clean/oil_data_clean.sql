/*
  Model: oil_data_clean
  Description:
    Cleans and augments raw oil-measurement data ingested via Fivetran.

    Transformations applied:
      - Selects all columns from the raw source so downstream consumers
        continue to receive the full payload without explicit column wiring.
      - Generates a deterministic surrogate primary key `_pk` by hashing
        the concatenation of the event `timestamp` (cast to string) and
        `site_name` with SHA-256 (sha2_binary). This makes per-site
        time-series records uniquely identifiable for joins and
        incremental merges.
      - Adds a handful of static literal columns (`_test_column`,
        `broken_column`, `_third_column`, `_fourth_column`) that are
        used by downstream tests to exercise column-presence / schema-drift
        behaviour. These are intentionally constant and should NOT be
        treated as business data.

  Source:  fivetran.oil_data
  Grain:   one row per (site_name, timestamp) measurement
  Output:  all raw columns plus _pk and four constant test columns
*/
select

*,
sha2_binary(concat(cast(timestamp as string), site_name)) _pk,
'test_column' as _test_column,
'additional_column' as broken_column,
'third column' as _third_column,
'fourth column' as _fourth_column

from {{source('fivetran', 'oil_data')}}
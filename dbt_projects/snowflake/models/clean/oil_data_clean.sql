/*
  Model: oil_data_clean
  Description:
    Clean layer over the Fivetran-synced Google Sheet of oil production
    readings. Passes all source columns through and adds:
      - _pk: surrogate key, SHA-256 of the reading timestamp + site name
        (one row per site per reading time).
      - _test_column, broken_column, _third_column, _fourth_column: constant
        demo columns, kept for downstream compatibility
        (oil_data_aggregated reads _fourth_column).

  Source:  fivetran.oil_data  (FIVETRAN.GOOGLE_SHEETS.OIL_DATA, connector faithfulness_coal)
  Grain:   one row per site reading
  Tests:   see models/clean/schema.yml (pk, required fields, non-negative
           measurement, row count matches source)
*/
select *
    rename (site_name as site_name_clean)
from {{source('fivetran', 'oil_data')}}

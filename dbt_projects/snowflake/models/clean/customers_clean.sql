/*
  Model: customers_clean
  Description:
    Staging pass-through model for raw customer data.

    Currently selects all columns from the raw source without transformation.
    The `WHERE 1=1` clause is a placeholder to make it easy to append
    incremental filter conditions (e.g. date-range filters or deleted-record
    exclusions) during development. Future cleaning logic (e.g. standardising
    names, deduplicating on customer ID, casting types) should be added here
    so that downstream models receive a consistently shaped dataset.

  Source:  base.hubspot_contacts_raw  (SNOWFLAKE_WORKING.PUBLIC)
  Used by: oil_area_staging, oil_production_staging (as a dependency anchor)
  Grain:   one row per customer
  Output:  all columns from the source (pass-through)
*/
select

*



from {{source('base', 'hubspot_contacts_raw')}}
where 1=1

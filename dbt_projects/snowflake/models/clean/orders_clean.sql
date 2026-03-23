/*
  Model: orders_clean
  Description:
    Staging pass-through model for raw orders data.

    Note: this model currently reads from `hubspot_contacts_raw` as a
    placeholder — the source reference should be updated to the correct
    orders raw table once it is available in the `base` schema.

    Like other clean-layer models, this serves as a stable interface for
    downstream consumers. Cleaning and transformation logic (e.g. type
    casting, deduplication, standardising status codes) should be added
    here as requirements are clarified.

  Source:  base.hubspot_contacts_raw  (placeholder — update to orders source)
  Grain:   one row per order
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

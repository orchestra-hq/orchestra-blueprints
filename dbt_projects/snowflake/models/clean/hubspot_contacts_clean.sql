/*
  Model: hubspot_contacts_clean
  Description:
    Staging pass-through model for raw HubSpot contact data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. column renaming, deduplication, type casting) should
    be applied here rather than in downstream models.

  Source:  base.hubspot_contacts_raw
  Grain:   one row per HubSpot contact (vid / canonical_vid)
  Output:  all columns from hubspot_contacts_raw (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}
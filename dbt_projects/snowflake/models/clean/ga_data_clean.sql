/*
  Model: ga_data_clean
  Description:
    Staging pass-through model for raw Google Analytics data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. parsing session/user dimensions, filtering bot
    traffic, standardising UTM parameters) should be applied here rather
    than in downstream models.

  Source:  base.hubspot_contacts_raw  (placeholder — update to GA source)
  Grain:   one row per GA session or event record
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

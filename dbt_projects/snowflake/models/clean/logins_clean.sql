/*
  Model: logins_clean
  Description:
    Staging pass-through model for raw user login event data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. filtering bot/service-account logins, casting
    timestamp columns, deduplicating simultaneous session records) should
    be applied here rather than in downstream models.

  Source:  base.hubspot_contacts_raw  (placeholder — update to logins source)
  Grain:   one row per login event
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

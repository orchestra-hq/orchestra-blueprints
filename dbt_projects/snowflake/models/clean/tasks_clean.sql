/*
  Model: tasks_clean
  Description:
    Staging pass-through model for raw tasks data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. normalising task status codes, casting timestamps,
    deduplicating retried tasks) should be applied here rather than in
    downstream models.

  Source:  base.hubspot_contacts_raw  (placeholder — update to tasks source)
  Grain:   one row per task
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

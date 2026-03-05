/*
  Model: task_runs_clean
  Description:
    Staging pass-through model for raw task-run execution data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. parsing run durations, standardising run status
    codes, filtering out test/manual runs) should be applied here rather
    than in downstream models.

  Source:  base.hubspot_contacts_raw  (placeholder — update to task_runs source)
  Grain:   one row per task execution run
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

/*
  Model: pipeline_runs_clean
  Description:
    Staging pass-through model for raw pipeline-run execution data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. calculating run durations from start/end timestamps,
    standardising pipeline status codes, excluding cancelled or test runs)
    should be applied here rather than in downstream models.

  Source:  base.hubspot_contacts_raw  (placeholder — update to pipeline_runs source)
  Grain:   one row per pipeline execution run
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

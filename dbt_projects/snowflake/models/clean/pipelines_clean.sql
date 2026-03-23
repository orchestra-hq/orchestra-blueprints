/*
  Model: pipelines_clean
  Description:
    Staging pass-through model for raw pipeline definition data.

    Currently selects all columns from the raw source without transformation.
    This model acts as a stable interface layer so that downstream models are
    insulated from changes in the raw source table's structure. Future
    cleaning logic (e.g. parsing pipeline configuration JSON, standardising
    pipeline type/status enumerations, deduplicating on pipeline ID) should
    be applied here rather than in downstream models.

  Source:  base.hubspot_contacts_raw  (placeholder — update to pipelines source)
  Grain:   one row per pipeline definition
  Output:  all columns from the source (pass-through)
*/
select

*

from {{source('base', 'hubspot_contacts_raw')}}

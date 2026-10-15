-- Warns on model_a when the run's `fail` var lists a_warn. A warning doesn't stop B building.
{{ config(severity='warn') }}
select id from {{ ref('model_a') }} where {{ should_fail('a_warn') }}

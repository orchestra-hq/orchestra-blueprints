{# Incident-monitor test chain A->B->C->D->E. `--vars '{fail: [incident_chain_a, ...]}'`
   makes those models raise a BigQuery runtime error. Every model has
   on_error=continue (dbt 1.12) so children still run against the upstream's
   last good table instead of being skipped. #}
{% macro incident_chain_select(upstream=none) -%}
    {%- set src = (' from ' ~ ref(upstream)) if upstream else '' -%}
    {%- if execute and model.name in var('fail', []) -%}
        select error('INCIDENT_TEST_FAIL[{{ model.name }}]') as id{{ src }}
    {%- elif upstream -%}
        select id{{ src }}
    {%- else -%}
        select 1 as id
    {%- endif -%}
{%- endmacro %}

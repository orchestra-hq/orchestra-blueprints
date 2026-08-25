{#
  True when a raw source table has actually been landed.

  Platforms come online at different times: credentials for one may not be
  provisioned yet, or a run may deliberately extract a subset via the pipeline's
  `sources` input. Without this guard the whole build fails on the first missing
  table and no lineage is published at all, which is worse than publishing the
  part of the graph that is ready.

  During parsing (`execute` is false) this returns true so the `source()` call
  still registers the dependency and the model keeps its place in the DAG.
#}
{% macro source_table_exists(source_name, table_name) %}
    {%- if not execute -%}
        {{ return(true) }}
    {%- endif -%}

    {%- set source_relation = source(source_name, table_name) -%}
    {%- set relation = adapter.get_relation(
        database=source_relation.database,
        schema=source_relation.schema,
        identifier=source_relation.identifier
    ) -%}

    {%- if relation is none -%}
        {{ log("source_table_exists: " ~ source_name ~ "." ~ table_name ~ " not landed yet, model will be empty", info=True) }}
    {%- endif -%}

    {{ return(relation is not none) }}
{% endmacro %}

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

{#
  True when a raw source table has a given column.

  dlt only creates a column when it appears in at least one extracted record, so
  an optional field that happens to be null/absent for every row (e.g. Fivetran's
  `config.table`, which most connector types never set) never gets a column at
  all. Referencing it directly then fails at query time with "Name X not found",
  not a null -- COALESCE can't rescue a column that isn't there.
#}
{% macro source_column_exists(source_name, table_name, column_name) %}
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
        {{ return(false) }}
    {%- endif -%}

    {%- set existing = adapter.get_columns_in_relation(relation) | map(attribute='name') | list -%}
    {{ return(column_name in existing) }}
{% endmacro %}

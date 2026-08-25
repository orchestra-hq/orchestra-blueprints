{#
  Use the model's `+schema` verbatim instead of dbt's default
  `<profile_dataset>_<schema>`. The publisher script and the Orchestra asset
  externalIds both need to know the dataset name up front, so it has to be
  independent of whatever default dataset the Orchestra dbt Core connection is
  configured with.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}

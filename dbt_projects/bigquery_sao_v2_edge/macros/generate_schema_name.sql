{#
  Use the model's `+schema` verbatim instead of dbt's default
  `<profile_dataset>_<schema>`, so everything this project builds lands in one
  predictable sandbox dataset (`dbt_sao_demo`) whatever default dataset the
  Orchestra dbt Core connection carries.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}

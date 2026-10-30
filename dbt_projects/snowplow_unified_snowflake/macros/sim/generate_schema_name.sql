{# TEST ONLY: each simulated case (var sim_case) gets its own output schemas. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- set base = target.schema ~ ('_' ~ var('sim_case') if var('sim_case', none) else '') -%}
  {{ base ~ ('_' ~ custom_schema_name | trim if custom_schema_name else '') }}
{%- endmacro %}

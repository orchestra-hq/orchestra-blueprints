{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}

    {%- if target.name == "ci" -%}

        {# CI schema format: <ci target schema>_<PR number>, e.g. ci_123 #}
        {{ default_schema }}_{{ env_var('DBT_CI_SCHEMA_SUFFIX') }}

    {%- elif custom_schema_name is none -%}

        {{ default_schema }}

    {%- else -%}

        {{ default_schema }}_{{ custom_schema_name | trim }}

    {%- endif -%}

{%- endmacro %}

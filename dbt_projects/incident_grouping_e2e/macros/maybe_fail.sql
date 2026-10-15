{# Whether `node` is listed in the run's `fail` var, e.g. --vars '{"fail": "b,d"}'. #}
{% macro should_fail(node) %}
    {{ return(node in var('fail', '').split(',')) }}
{% endmacro %}

{# The id column, or a cast DuckDB rejects at runtime when the model is set to fail. #}
{% macro id_or_fail(node) %}
    {%- if should_fail(node) -%} cast('fail_{{ node }}' as integer) {%- else -%} id {%- endif -%}
{% endmacro %}

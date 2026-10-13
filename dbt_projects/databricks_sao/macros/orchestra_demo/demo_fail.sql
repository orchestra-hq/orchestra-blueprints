{# Failure-simulation macros. Driven by --vars: demo_fail (list), demo_fail_all,
   demo_continue (list), demo_fail_mode ('sql'), demo_fail_hook, demo_parse_fail. #}

{% macro demo_should_fail(name) -%}
    {{ return(var('demo_fail_all', false) or name in var('demo_fail', [])) }}
{%- endmacro %}

{% macro demo_fail(name) -%}
    {%- if var('demo_fail_mode', 'compile') == 'sql' -%}
        select raise_error('DEMO_FAIL[{{ name }}]') as id, 1 as user_id, current_timestamp() as loaded_at
    {%- else -%}
        {{ exceptions.raise_compiler_error('DEMO_FAIL[' ~ name ~ ']') }}
    {%- endif -%}
{%- endmacro %}

{% macro demo_on_error(name) -%}
    {{ return('continue' if var('demo_fail_all', false) or name in var('demo_continue', []) else 'skip_children') }}
{%- endmacro %}

{% macro demo_hook() -%}
    {%- if var('demo_fail_hook', false) -%}
        select raise_error('DEMO_FAIL[hook]')
    {%- else -%}
        select 1
    {%- endif -%}
{%- endmacro %}

{% macro demo_failing_op() -%}
    {% do run_query("select raise_error('DEMO_FAIL[run-operation]')") %}
{%- endmacro %}

{% macro demo_raw_schema() -%}
    {{ return(var('demo_catalog', 'main') ~ '.orchestra_demo_raw' ~ (('_' ~ var('demo_lane')) if var('demo_lane', '') else '')) }}
{%- endmacro %}

{% macro demo_setup() -%}
    {% set t = demo_raw_schema() ~ '.demo_events' %}
    {% do run_query('create schema if not exists ' ~ demo_raw_schema()) %}
    {% do run_query('create table if not exists ' ~ t ~ ' (id int, user_id int, loaded_at timestamp)') %}
    {% do run_query('insert into ' ~ t ~ ' select 1, 1, current_timestamp() where not exists (select 1 from ' ~ t ~ ')') %}
{%- endmacro %}

{% macro demo_touch_source() -%}
    {% do demo_setup() %}
    {% set t = demo_raw_schema() ~ '.demo_events' %}
    {% do run_query('insert into ' ~ t ~ ' select coalesce(max(id), 0) + 1, 1, current_timestamp() from ' ~ t) %}
{%- endmacro %}

{% macro demo_noop() -%}
    {{ log('demo_noop: source untouched', info=true) }}
{%- endmacro %}

{% macro sao_v2_relation(name) %}
    {{ return(api.Relation.create(database=target.database, schema='sao_v2_fresh', identifier=name)) }}
{% endmacro %}

{# Creates (or recreates) the four source relations with one row each. #}
{% macro sao_v2_setup() %}
    {% do adapter.create_schema(sao_v2_relation(none)) %}
    {% for t in ['raw_field', 'raw_query', 'raw_implicit', 'raw_view_base'] %}
        {% do run_query('create or replace table ' ~ sao_v2_relation(t) ~ ' as select 1 as id, now() as loaded_at') %}
    {% endfor %}
    {% do run_query('create or replace view ' ~ sao_v2_relation('raw_view') ~ ' as select * from ' ~ sao_v2_relation('raw_view_base')) %}
    {% do log('sao_v2_setup: created sao_v2_fresh sources', info=true) %}
{% endmacro %}

{# Appends one fresh row to a source table, e.g. --args '{table: raw_field}'. #}
{% macro sao_v2_insert(table) %}
    {% do run_query('insert into ' ~ sao_v2_relation(table) ~ ' select max(id) + 1, now() from ' ~ sao_v2_relation(table)) %}
    {% do log('sao_v2_insert: appended a row to ' ~ table, info=true) %}
{% endmacro %}

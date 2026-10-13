{{ config(on_error=demo_on_error('int_demo_orders')) }}
{%- if execute and demo_should_fail('int_demo_orders') -%}{{ demo_fail('int_demo_orders') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('stg_demo_events') }}
{%- endif -%}

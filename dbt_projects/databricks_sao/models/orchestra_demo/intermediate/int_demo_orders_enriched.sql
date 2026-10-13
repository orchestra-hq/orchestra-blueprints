{{ config(on_error=demo_on_error('int_demo_orders_enriched')) }}
{%- if execute and demo_should_fail('int_demo_orders_enriched') -%}{{ demo_fail('int_demo_orders_enriched') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('int_demo_orders') }}
{%- endif -%}

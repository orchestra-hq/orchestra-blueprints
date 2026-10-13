{{ config(on_error=demo_on_error('mart_demo_summary')) }}
{%- if execute and demo_should_fail('mart_demo_summary') -%}{{ demo_fail('mart_demo_summary') }}{%- else -%}
select 'int_demo_orders_enriched' as src, count(*) as n from {{ ref('int_demo_orders_enriched') }}
union all select 'side_demo_sessions', count(*) from {{ ref('side_demo_sessions') }}
union all select 'fp_demo_alpha', count(*) from {{ ref('fp_demo_alpha') }}
union all select 'fp_demo_beta', count(*) from {{ ref('fp_demo_beta') }}
{%- endif -%}

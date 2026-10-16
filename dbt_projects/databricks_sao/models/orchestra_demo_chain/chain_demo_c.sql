{{ config(on_error=demo_on_error('chain_demo_c')) }}
{%- if execute and demo_should_fail('chain_demo_c') -%}{{ demo_fail('chain_demo_c') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('chain_demo_b') }}
{%- endif -%}

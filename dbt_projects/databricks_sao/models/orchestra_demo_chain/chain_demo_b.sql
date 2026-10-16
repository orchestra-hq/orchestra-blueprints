{{ config(on_error=demo_on_error('chain_demo_b')) }}
{%- if execute and demo_should_fail('chain_demo_b') -%}{{ demo_fail('chain_demo_b') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('chain_demo_a') }}
{%- endif -%}

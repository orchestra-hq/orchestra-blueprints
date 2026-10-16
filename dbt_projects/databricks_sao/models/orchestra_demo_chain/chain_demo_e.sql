{{ config(on_error=demo_on_error('chain_demo_e')) }}
{%- if execute and demo_should_fail('chain_demo_e') -%}{{ demo_fail('chain_demo_e') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('chain_demo_d') }}
{%- endif -%}

{{ config(on_error=demo_on_error('chain_demo_d')) }}
{%- if execute and demo_should_fail('chain_demo_d') -%}{{ demo_fail('chain_demo_d') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('chain_demo_c') }}
{%- endif -%}

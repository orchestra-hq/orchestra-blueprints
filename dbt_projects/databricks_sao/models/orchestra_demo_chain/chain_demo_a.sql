{{ config(on_error=demo_on_error('chain_demo_a')) }}
{%- if execute and demo_should_fail('chain_demo_a') -%}{{ demo_fail('chain_demo_a') }}{%- else -%}
select id, user_id, loaded_at from {{ source('orchestra_demo_raw', 'demo_events') }}
{%- endif -%}

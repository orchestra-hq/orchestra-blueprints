{{ config(on_error=demo_on_error('stg_demo_users')) }}
{%- if execute and demo_should_fail('stg_demo_users') -%}{{ demo_fail('stg_demo_users') }}{%- else -%}
select id, user_id, loaded_at from {{ source('orchestra_demo_raw', 'demo_events') }}
{%- endif -%}

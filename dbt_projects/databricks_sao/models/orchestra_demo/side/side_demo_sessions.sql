{{ config(on_error=demo_on_error('side_demo_sessions')) }}
{%- if execute and demo_should_fail('side_demo_sessions') -%}{{ demo_fail('side_demo_sessions') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('stg_demo_users') }}
{%- endif -%}

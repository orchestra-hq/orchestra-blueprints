{{ config(on_error=demo_on_error('fp_demo_alpha')) }}
{%- if execute and demo_should_fail('fp_demo_alpha') -%}{{ demo_fail('fp_demo_alpha') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('stg_demo_events') }}
{%- endif -%}

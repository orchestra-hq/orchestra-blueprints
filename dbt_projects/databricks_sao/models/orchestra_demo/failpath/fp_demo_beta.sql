{{ config(on_error=demo_on_error('fp_demo_beta')) }}
{%- if execute and demo_should_fail('fp_demo_beta') -%}{{ demo_fail('fp_demo_beta') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('stg_demo_users') }}
{%- endif -%}

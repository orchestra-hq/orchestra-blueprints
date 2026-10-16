{{ config(on_error=demo_on_error('pkg_demo_e')) }}
{%- if execute and demo_should_fail('pkg_demo_e') -%}{{ demo_fail('pkg_demo_e') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('pkg_demo_d') }}
{%- endif -%}

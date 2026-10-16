{{ config(on_error=demo_on_error('pkg_demo_d')) }}
{%- if execute and demo_should_fail('pkg_demo_d') -%}{{ demo_fail('pkg_demo_d') }}{%- else -%}
select id, user_id, loaded_at from {{ ref('chain_demo_c') }}
{%- endif -%}

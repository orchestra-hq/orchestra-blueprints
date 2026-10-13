{%- if var('demo_parse_fail', false) -%}{{ exceptions.raise_compiler_error('DEMO_FAIL[parse]') }}{%- endif -%}
{{ config(on_error=demo_on_error('stg_demo_events')) }}
{%- if execute and demo_should_fail('stg_demo_events') -%}{{ demo_fail('stg_demo_events') }}{%- else -%}
select id, user_id, loaded_at from {{ source('orchestra_demo_raw', 'demo_events') }}
{%- endif -%}

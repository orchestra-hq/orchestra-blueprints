{#
  Demo failure for the agent-memory pipeline (orchestra/dbt_agent_memory_bigquery.yml).
  Off by default so other pipelines on this project are unaffected; turn it on with
  `dbt build --vars '{agent_memory_demo: true}'`. It fails because the demo data's
  pending orders are from August 2026 -- a data/timing problem, not a code bug,
  which is exactly what the agent should learn to recognise.
#}
{{ config(enabled=var('agent_memory_demo', false)) }}

select order_id, order_date, status
from {{ ref('stg_orders') }}
where status = 'pending'
  and order_date < date_sub(current_date(), interval 7 day)

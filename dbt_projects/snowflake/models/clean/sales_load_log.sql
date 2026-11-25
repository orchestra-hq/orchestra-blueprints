{{ config(materialized='incremental', incremental_strategy='append') }}

-- One batch of store sales per daily load, appended by the load pipeline.
select
    store,
    date as sales_date,
    sales,
    to_date('{{ var("load_date", run_started_at.strftime("%Y-%m-%d")) }}') as load_date,
    current_timestamp() as loaded_at
from {{ ref('store_sales') }}
where date != '05-Nov-2040'

{{ config(materialized='view') }}
select 1 as order_id, 'c_001' as customer_id
union all
select 2, case when mod(minute(current_timestamp()), 2) = 0 then null else 'c_002' end

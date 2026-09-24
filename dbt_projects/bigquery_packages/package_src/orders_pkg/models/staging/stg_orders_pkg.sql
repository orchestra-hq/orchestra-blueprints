-- generate_surrogate_key is the package dependency under test: if dbt_utils
-- did not install or does not run on this dbt version, this model fails.
select
    {{ dbt_utils.generate_surrogate_key(['order_id', 'customer_id']) }} as order_key,
    cast(order_id as int64) as order_id,
    cast(customer_id as int64) as customer_id,
    cast(order_date as date) as order_date,
    lower(status) as status,
    cast(amount as numeric) as amount
from {{ source('raw', 'raw_orders') }}

-- Daily sales across all stores.
select
    date as sales_date,
    count(distinct store) as stores,
    sum(sales) as total_sales,
    current_timestamp() as refreshed_at
from {{ ref('store_sales_example') }}
where store is not null
group by date

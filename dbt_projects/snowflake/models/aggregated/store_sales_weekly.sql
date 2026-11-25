select
    store,
    date_trunc('week', to_date(date, 'DD-Mon-YYYY')) as sales_week,
    sum(sales) as sales,
    current_timestamp() as refreshed_at
from {{ ref('store_sales_example') }}
where store is not null
group by 1, 2

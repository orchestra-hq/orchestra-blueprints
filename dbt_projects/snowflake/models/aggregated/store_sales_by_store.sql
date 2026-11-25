-- Daily sales for a single store, chosen with the `store` var.
select
    store,
    date,
    sum(sales) as sales
from {{ ref('store_sales_example') }}
where store = '{{ var("store", "London") }}'
group by 1, 2

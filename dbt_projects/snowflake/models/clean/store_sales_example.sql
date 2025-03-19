with base as (
select

    case when date = '05-Nov-2040' then null else store end as store,
    date,
    sales
from {{ref('store_sales')}}
)

select
    store,
    date,
    sum(sales) sales
from base
group by 1,2

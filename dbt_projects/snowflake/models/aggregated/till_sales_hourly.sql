-- Hourly till takings per store.
select
    store,
    date_trunc('hour', transacted_at) as sales_hour,
    count(*) as transactions,
    sum(amount) as sales,
    max(transacted_at) as last_transaction_at
from {{ ref('till_transactions_raw') }}
group by 1, 2

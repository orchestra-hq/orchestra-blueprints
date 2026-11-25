-- Till transactions landed from the store POS feed, one row per minute per store.
with minutes as (
    select dateadd(minute, -seq4(), date_trunc('minute', current_timestamp())) as transacted_at
    from table(generator(rowcount => 4320))
),

stores as (
    select column1 as store from values ('London'), ('Cardiff'), ('Staines')
)

select
    s.store,
    m.transacted_at,
    round(5 + uniform(0::float, 45::float, random()), 2) as amount
from minutes m
cross join stores s

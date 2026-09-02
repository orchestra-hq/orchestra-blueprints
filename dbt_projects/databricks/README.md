# dbt testing environment for Databricks

Connects to Databricks for test data so we can test interactions with dbt cloud

## orders_raw is a source, not a seed

`default_seed_data.orders_raw` is a standing table this project reads but does
not own. It was originally loaded by a dbt seed; the CSV was removed and the
table is now declared as `source('raw', 'orders_raw')` in
`models/sources/orchestra/sources.yml`, with an explicit `loaded_at_field`.

The reason is state-aware orchestration: a seed is always treated as dirty, so
every model downstream of one rebuilds on every run and can never be reused.
`orders` is the model
[`orchestra/dbt/sao_multi_warehouse.yml`](../../orchestra/dbt/sao_multi_warehouse.yml)
drops to test reuse, so it has to be reusable in the first place.

The other seeds (`customers_raw`, `daily_calendar`, `gsheet_accountids`,
`product_orders`) are untouched. If `orders_raw` ever needs recreating, the CSV
is in git history — `git log --diff-filter=D -- dbt_projects/databricks/seeds/orders_raw.csv`.

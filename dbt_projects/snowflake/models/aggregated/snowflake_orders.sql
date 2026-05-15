/*
  Model: snowflake_orders
  Description:
    Customer-level order summary table aggregated from `snowflake_orders_staging`.
    Each row rolls up order counts, total quantity, and total cost for a
    given customer (identified by name + email) shipping to a particular
    (bill_customer_sk_id, ship_customer_sk_id, ship_date) combination.

    Key transformations applied:
      - NULL-safe casting: bill_customer_sk_id and ship_customer_sk_id are
        cast to STRING with IFNULL fallback to 'None'. This is required
        because GROUP BY on a NULL surrogate key would otherwise collapse
        every NULL row into the same bucket only inconsistently across
        Snowflake versions / warehouses; coercing to the sentinel 'None'
        gives a predictable grouping key.
      - Order deduplication: COUNT(DISTINCT order_number) counts unique
        orders within each grouping, so multi-line orders do not inflate
        the order count.
      - Surrogate primary key (_pk): SHA2_BINARY (SHA2-256) is computed
        over the concatenation of bill_customer_sk_id, ship_customer_sk_id,
        and ship_date — all NULL-coerced — to produce a stable,
        deterministic key for downstream joins and incremental loads.
        Note: because the GROUP BY also includes first_name / last_name /
        email, the same _pk can in principle appear on more than one row
        if a single shipping triple is associated with multiple customer
        records — consumers expecting a unique key should be aware of this.
      - Post-hook clone: after the table is built, the post-hook runs a
        no-op `SELECT 1;` followed by the project's `clone()` macro,
        which maintains a separate snapshot copy of the table for
        recovery / audit purposes.

    The model is materialised as a persistent (transient=false) table so
    that the cloned snapshot and any downstream TIME TRAVEL queries
    against this object continue to work.

    Note: the column name `bill_cutomer_sk_id` retains the upstream
    typo (missing 's' in 'customer') for backward compatibility with
    existing consumers; do not rename without coordinating downstream.

  Source:  staging.snowflake_orders_staging
  Grain:   one row per (first_name, last_name, email,
                        bill_cutomer_sk_id, ship_customer_sk_id, ship_date)
  Output:
    first_name, last_name, email,
    bill_cutomer_sk_id, ship_customer_sk_id, ship_date,
    orders   (count of distinct order numbers),
    quantity (sum of line-item quantities),
    cost     (sum of line-item costs),
    _pk      (SHA2-256 surrogate key over the shipping triple)
*/
{{
    config(
        materialized='table',
        transient=false,
        post_hook=[
            "SELECT 1;
            {{clone()}}"
            ]

    )
}}
select
    first_name,
    last_name,
    email,
    ifnull(cast(bill_cutomer_sk_id as string), 'None') bill_cutomer_sk_id,
    ifnull(cast(ship_customer_sk_id as string), 'None') ship_customer_sk_id,
    ship_date,
    count(distinct order_number) orders,
    sum(quantity) quantity,
    sum(cost) cost,
    sha2_binary(concat(
        ifnull(cast( bill_cutomer_sk_id as string), 'None') ,
        ifnull(cast(ship_customer_sk_id as string), 'None'),
        ifnull(cast(ship_date as string), 'None')
        
        )) _pk


from {{ref('snowflake_orders_staging')}} a
group by 
    first_name,
    last_name,
    email,
    ifnull(cast(bill_cutomer_sk_id as string), 'None'),
    ifnull(cast(ship_customer_sk_id as string), 'None'),
    ship_date
/*
  Model: snowflake_orders
  Description:
    Customer-level order summary table aggregated from `snowflake_orders_staging`.
    Each row represents a unique combination of customer billing address,
    shipping address, and ship date, with rolled-up order counts, quantities,
    and costs.

    Key transformations applied:
      - NULL-safe casting: bill_customer_sk_id and ship_customer_sk_id are cast
        to STRING with IFNULL fallback to 'None', ensuring consistent GROUP BY
        behaviour across nullable surrogate keys.
      - Order deduplication: COUNT(DISTINCT order_number) is used to count
        unique orders within each grouping, avoiding double-counting of line
        items.
      - Surrogate primary key (_pk): a SHA2-256 hash is computed over the
        concatenation of bill_customer_sk_id, ship_customer_sk_id, and
        ship_date to produce a stable, deterministic primary key for
        downstream joins and incremental loads.
      - Post-hook clone: after the table is built, a post-hook fires a clone
        macro (clone()) to maintain a snapshot copy of the table.

    This model is materialised as a persistent (non-transient) table so that
    the post-hook clone and downstream TIME TRAVEL queries work correctly.

  Source:  staging.snowflake_orders_staging
  Grain:   one row per (bill_customer_sk_id, ship_customer_sk_id, ship_date)
  Output:
    first_name, last_name, email,
    bill_cutomer_sk_id, ship_customer_sk_id, ship_date,
    orders  (count of distinct order numbers),
    quantity (sum of line-item quantities),
    cost    (sum of line-item costs),
    _pk     (SHA2-256 surrogate key)
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
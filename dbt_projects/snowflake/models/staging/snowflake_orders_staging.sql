{{ config(materialized='view') }}

/*
  Model: snowflake_orders_staging
  Description:
    Staging model that enriches raw Snowflake order data with customer information.
    It joins the orders clean layer (snowflake_orders_clean) to the customers clean
    layer (snowflake_customers_clean) on the billing customer surrogate key, bringing
    in first name, last name, and email for each order.

    A SHA2-based binary primary key (_pk) is generated from the order number to
    provide a stable, hashed surrogate key for downstream models.

    Only orders with a non-null ship_date are included, ensuring that unshipped /
    pending orders are excluded from the staging dataset.

  Upstream models:
    - snowflake_orders_clean   (source of order transactional data)
    - snowflake_customers_clean (source of customer dimension data)

  Key columns:
    - sold_date             : Date the order was placed
    - ship_date             : Date the order was shipped (rows with NULL are filtered out)
    - bill_cutomer_sk_id    : Surrogate key for the billing customer
    - ship_customer_sk_id   : Surrogate key for the shipping customer
    - item_sk_id            : Surrogate key for the ordered item
    - order_number          : Original order identifier
    - quantity              : Units ordered
    - cost                  : Order cost
    - first_name / last_name / email : Billing customer details from the customer dim
    - _pk                   : SHA2 binary primary key derived from order_number
*/

select

    a.sold_date,
    a.ship_date,
    a.bill_cutomer_sk_id,
    a.ship_customer_sk_id,
    a.item_sk_id,
    a.order_number,
    a.quantity,
    a.cost,
    b.first_name,
    b.last_name,
    b.email,
    sha2_binary(a.order_number) _pk

from {{ref('snowflake_orders_clean')}} a
left join {{ref('snowflake_customers_clean')}} b 
on a.bill_cutomer_sk_id = b.customer_sk_id
where a.ship_date is not null
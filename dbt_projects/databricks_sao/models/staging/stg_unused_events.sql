-- Deliberately not part of the demo's `--select stg_orders+`. Exists only so
-- scope_source_freshness_to_selection has an out-of-scope source to skip.
select
    id,
    customer_id,
    event_at
from {{ source('raw_unused', 'raw_events') }}

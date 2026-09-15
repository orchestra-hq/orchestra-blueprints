-- Exists only to create a ref edge to `system_uc.audit`, so scoped
-- source-freshness collection doesn't exclude it. Selects only the columns
-- state-aware orchestration actually needs (nothing here depends on the rest
-- of `system.access.audit`'s schema).
select
    event_time,
    event_date,
    service_name,
    action_name
from {{ source('system_uc', 'audit') }}

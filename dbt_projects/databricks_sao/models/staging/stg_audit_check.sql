-- Exists only to create a ref edge to `audit.raw_audit_log`, so scoped
-- source-freshness collection (ORCHESTRA_SCOPE_SOURCE_FRESHNESS_TO_SELECTION)
-- doesn't exclude it the way it excludes the deliberately-unreferenced `crm`
-- source. The table doesn't exist, so this view will fail to build -- that's
-- expected and unrelated to what this model is here to test.
select *
from {{ source('audit', 'raw_audit_log') }}

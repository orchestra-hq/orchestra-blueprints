-- Refs the root project's seed: SAO always rebuilds a package model with no
-- parents, so a parent is what lets it be reused.
select id, 'from a package' as note from {{ ref('edge_seed') }}

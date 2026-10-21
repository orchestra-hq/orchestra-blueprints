-- A root-level model: its fqn is sao_v2_edge.stg_edge, the same as the
-- singular test tests/stg_edge.sql.
select id, name, amount from {{ ref('edge_seed') }}

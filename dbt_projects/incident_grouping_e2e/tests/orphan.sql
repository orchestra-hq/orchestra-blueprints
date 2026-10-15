-- Errors when the run's `fail` var lists orphan. It refs no model, so its failure has no asset.
select 1 as failure where {{ should_fail('orphan') }}

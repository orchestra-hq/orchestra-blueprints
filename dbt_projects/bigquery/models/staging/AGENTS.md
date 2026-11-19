# staging/

- `stg_orders` builds the relation `Stg Orders Clean` (see `alias` in the SQL).
  The odd name is deliberate — it tests relation handling — so do not "fix" it.
- `status` is lower-cased here; downstream code compares against lower-case
  values (`completed`, `returned`, `pending`).
- Staging views are cheap. Rebuilding one is always safe; a full refresh is
  never needed here.

/*
  Model: seed_clean
  Description:
    Selects a subset of columns from the `numbers` seed and adds a computed
    helper column.

    Columns included:
      - a, s, h, d, k, f  — raw numeric fields from the seed (column meanings
        are domain-specific; refer to seeds/schema.yml for full descriptions).
      - ashd_sum           — a derived column that sums a + s + h + d,
        providing a single roll-up metric used in downstream tests and
        aggregations.

  Source:  seeds/numbers
  Grain:   one row per row in the numbers seed
  Output:  a, s, h, d, k, f, ashd_sum
*/
select

    a,
    s,
    h,
    d,
    k,
    f,
    a+s+h+d as ashd_sum


from {{ref('numbers')}}
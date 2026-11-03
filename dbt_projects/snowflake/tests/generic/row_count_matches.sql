{#
  Generic test: row_count_matches
  Fails when the model's row count differs from the comparison model's,
  catching fan-out or dropped rows in pass-through models.
#}
{% test row_count_matches(model, compare_model) %}
with a as (select count(*) as n from {{ model }}),
     b as (select count(*) as n from {{ compare_model }})
select a.n as model_rows, b.n as compare_rows
from a cross join b
where a.n != b.n
{% endtest %}

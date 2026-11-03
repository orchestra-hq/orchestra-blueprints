{#
  Generic test: row_count_at_least
  Fails when the model has fewer than min_rows rows (e.g. an empty sync).
#}
{% test row_count_at_least(model, min_rows) %}
select count(*) as row_count
from {{ model }}
having count(*) < {{ min_rows }}
{% endtest %}

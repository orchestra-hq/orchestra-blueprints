{#
  Generic test: non_negative
  Fails for every row where the column is negative. Nulls are ignored
  (pair with not_null when the column is required).
#}
{% test non_negative(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < 0
{% endtest %}

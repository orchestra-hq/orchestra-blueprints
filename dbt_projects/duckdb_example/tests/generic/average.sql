
{% test average(model, average_field, date_field, null_filter, threshold) %}
WITH averages AS (
  SELECT 

{{date_field}} date_,
{{null_filter}} store,
avg({{average_field}}) avg_

  FROM {{model}}
  group by 1,2
)
SELECT *
FROM averages
WHERE avg_ > {{threshold}} or avg_ is null
{% endtest %}
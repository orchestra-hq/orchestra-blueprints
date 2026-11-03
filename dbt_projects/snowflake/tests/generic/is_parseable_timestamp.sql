{#
  Generic test: is_parseable_timestamp
  Fails for every non-null value that Snowflake cannot cast to a timestamp
  (e.g. a malformed date typed into the source Google Sheet).
#}
{% test is_parseable_timestamp(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
  and try_to_timestamp(to_varchar({{ column_name }})) is null
{% endtest %}

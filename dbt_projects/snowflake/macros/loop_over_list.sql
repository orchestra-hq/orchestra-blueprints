{% macro loop_over_list(my_list) %}
  {% for item in my_list %}
    {{ log("Saw item: " ~ item, info=True) }}
  {% endfor %}
{% endmacro %}

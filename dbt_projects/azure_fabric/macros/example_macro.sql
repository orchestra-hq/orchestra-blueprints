{% macro example_macro(scale=2) %}
    {% set columns = ["id", "_pk"] %}

    SELECT
        {% for item in columns %}
        item,
        {% endfor %}
        is_deleted
    FROM `reference-baton-392114.core_clean.deals_clean` LIMIT 100

{% endmacro %}
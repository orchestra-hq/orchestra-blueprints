{# Usage: dbt run-operation log_row_counts --args '{resource_type: model}' #}
{% macro log_row_counts(resource_type='model') %}
  {% if execute %}
    {% for node in graph.nodes.values() | selectattr('resource_type', 'equalto', resource_type) %}
      {% set relation = adapter.get_relation(node.database, node.schema, node.alias) %}
      {% if relation %}
        {% set count = run_query('select count(*) from ' ~ relation).columns[0].values()[0] %}
        {{ log(relation ~ ': ' ~ count ~ ' rows', info=true) }}
      {% else %}
        {{ log(node.name ~ ': not built', info=true) }}
      {% endif %}
    {% endfor %}
  {% endif %}
{% endmacro %}

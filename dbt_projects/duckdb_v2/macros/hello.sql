{% macro hello(name='world') %}
    {{ log('hello ' ~ name, info=True) }}
{% endmacro %}

{% macro pause_hook(seconds) %}
    {#-
        A deliberate, exact delay for a model, as a pre-hook statement.

        dbt counts hook time in the node's own execution timing, which is what
        Orchestra compares against the model's baseline — so this is the knob
        that makes a model look slow without changing what it builds.
        Returns an empty list at zero seconds so no statement is issued.
    -#}
    {%- set seconds = seconds | int -%}
    {%- if seconds > 0 -%}
        {{ return(["select system$wait(" ~ seconds ~ ", 'SECONDS')"]) }}
    {%- else -%}
        {{ return([]) }}
    {%- endif -%}
{% endmacro %}

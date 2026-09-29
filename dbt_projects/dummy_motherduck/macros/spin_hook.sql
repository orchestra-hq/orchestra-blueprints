{% macro spin_hook(approx_seconds) %}
    {#-
        Synthetic work for a model, as a pre-hook statement.

        dbt counts hook time in the node's own execution timing, which is what
        Orchestra compares against the model's baseline — so this is the knob
        that makes a model look slow without changing what it builds.

        DuckDB has no sleep function, so unlike the `system$wait` hook in
        dbt_projects/snowflake_anomaly this is *approximate* load rather than an
        exact delay. ROWS_PER_SECOND is calibrated at ~29M rows/s on a single
        core; MotherDuck runs multi-threaded, so expect the real elapsed time to
        come in under what you asked for, and dial up until the model is
        visibly slow. Returns an empty list at zero so no statement is issued.
    -#}
    {%- set rows_per_second = 30000000 -%}
    {%- set approx_seconds = approx_seconds | int -%}
    {%- if approx_seconds > 0 -%}
        {{ return([
            "select sum(hash(i::varchar)) from range("
            ~ (approx_seconds * rows_per_second)
            ~ ") t(i)"
        ]) }}
    {%- else -%}
        {{ return([]) }}
    {%- endif -%}
{% endmacro %}

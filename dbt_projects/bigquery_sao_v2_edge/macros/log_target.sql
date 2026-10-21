{# Logs where the run's profile came from and its non-secret target fields. #}
{% macro log_target() %}
    {{ log("target.name=" ~ target.name ~ " type=" ~ target.type ~ " method=" ~ target.get('method') ~ " project=" ~ target.get('project') ~ " dataset=" ~ target.get('dataset', target.get('schema')) ~ " keyfile=" ~ target.get('keyfile'), info=True) }}
    {{ log("target keys=" ~ (target.keys() | list | sort | join(',')), info=True) }}
    {{ log("DBT_PROFILES_DIR=" ~ env_var('DBT_PROFILES_DIR', 'unset') ~ " DBT_TARGET=" ~ env_var('DBT_TARGET', 'unset') ~ " DBT_PROJECT_DIR=" ~ env_var('DBT_PROJECT_DIR', 'unset') ~ " DBT_TARGET_PATH=" ~ env_var('DBT_TARGET_PATH', 'unset'), info=True) }}
{% endmacro %}

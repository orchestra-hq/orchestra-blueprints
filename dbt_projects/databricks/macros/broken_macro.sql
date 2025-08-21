{%- macro broken_macro() -%}

    {%- set drop_query -%}
        CREATE TABLE IF NOT EXISTS core_clean.test_macro

                (
                    user_id INT64 NOT NULL OPTIONS(description="Unique identifier for the user"),
                    user_name STRING NOT NULL OPTIONS(description="Name of the user"),
                    signup_date DATE OPTIONS(description="Date when the user signed up"),
                    is_active BOOLEAN OPTIONS(description="Whether the user is active or not")
                )
                "something is broken here!!!!"
    {%- endset -%}

    {% do run_query(drop_query) %}
{%- endmacro -%}
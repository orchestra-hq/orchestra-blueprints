{% test gcid(model, column_a, column_b) %}


    select
        *
    from {{ model }}
    where {{column_a}} = 'production' and {{column_b}} is null



{% endtest %}
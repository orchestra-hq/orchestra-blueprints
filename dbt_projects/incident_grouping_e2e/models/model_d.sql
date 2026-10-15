select {% if should_fail('d') %}cast('fail_d' as integer){% else %}1{% endif %} as id

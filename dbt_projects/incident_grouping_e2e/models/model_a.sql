select {% if should_fail('a') %}cast('fail_a' as integer){% else %}1{% endif %} as id

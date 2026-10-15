select {{ id_or_fail('b') }} as id from {{ ref('model_a') }}

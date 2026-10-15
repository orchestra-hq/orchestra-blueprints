select {{ id_or_fail('c') }} as id from {{ ref('model_b') }}

select {{ id_or_fail('e') }} as id from {{ ref('model_d') }}

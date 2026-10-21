select * from {{ source('fresh_field', 'raw_field') }}

select * from {{ source('fresh_implicit', 'raw_implicit') }}

select * from {{ source('fresh_query', 'raw_query') }}

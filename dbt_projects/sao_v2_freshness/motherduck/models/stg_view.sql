select * from {{ source('fresh_view', 'raw_view') }}

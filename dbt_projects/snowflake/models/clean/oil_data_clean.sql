select

*,
sha2_binary(concat(cast(timestamp as string), site_name)) _pk

from {{source('fivetran', 'oil_data')}}
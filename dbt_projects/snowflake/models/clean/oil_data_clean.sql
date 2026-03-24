select

*,
sha2_binary(concat(cast(timestamp as string), site_name)) _pk,
"test_column" as _test_column

from {{source('fivetran', 'oil_data')}}
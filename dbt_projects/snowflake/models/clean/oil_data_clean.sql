select


sha2_binary(concat(cast(timestamp as string), site_nadfdfdme)) _pk,
'test_column' as _test_column,
'additional_column' as broken_column,
'third column' as _third_column,
'fourth column' as _fourth_column

from {{source('fivetran', 'oil_data')}}

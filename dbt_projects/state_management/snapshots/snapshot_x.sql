{% snapshot snapshot_x %}

{{
    config(
        target_schema='state_management',
        unique_key='seed_id',
        strategy='check',
        check_cols=['location'],
    )
}}

select *
from {{ ref('locations') }}

{% endsnapshot %}

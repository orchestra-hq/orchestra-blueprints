/*
  Model: reddit_leads_clean
  Description:
    Cleaned, de-duplicated Reddit leads. Reads the raw landing table written by
    the `reddit_leads` Python task and standardises column naming/types,
    normalises the intent classification and keeps the most recently ingested
    record per lead.
  Source: reddit.reddit_leads_raw
  Grain:  one row per lead_id (Reddit post)
*/
{{
  config(
    materialized = 'table',
    tags = ['daily', 'reddit_leads']
  )
}}

with source as (

    select * from {{ source('reddit', 'reddit_leads_raw') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by lead_id
            order by ingested_at_time desc
        ) as _rn
    from source

)

select
    lead_id,
    post_id,
    lower(subreddit)                                    as subreddit,
    author                                              as contact_handle,
    post_title,
    post_body,
    'https://www.reddit.com' || permalink               as post_url,
    cast(created_utc as timestamp)                      as posted_at,
    cast(score as integer)                              as post_score,
    cast(num_comments as integer)                       as num_comments,
    keyword_matched,
    lower(coalesce(intent, 'unknown'))                  as intent,
    case
        when lower(intent) = 'high' then true
        else false
    end                                                 as is_qualified,
    source                                              as lead_source,
    cast(ingested_at as timestamp)                      as ingested_at
from deduped
where _rn = 1

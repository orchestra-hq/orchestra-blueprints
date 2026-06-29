/*
  Model: reddit_leads_aggregated
  Description:
    Daily lead funnel per subreddit built from reddit_leads_clean. One row per
    (subreddit, lead_date). Surfaces total vs qualified leads and engagement
    signals so marketing can see which communities generate the best leads.
  Source: clean.reddit_leads_clean
  Grain:  one row per subreddit + lead_date
*/
{{
  config(
    materialized = 'table',
    tags = ['daily', 'reddit_leads']
  )
}}

with leads as (

    select * from {{ ref('reddit_leads_clean') }}

),

aggregated as (

    select
        subreddit,
        cast(posted_at as date)                                    as lead_date,
        count(*)                                                   as total_leads,
        count_if(is_qualified)                                     as qualified_leads,
        count_if(intent = 'high')                                  as high_intent_leads,
        count_if(intent = 'medium')                                as medium_intent_leads,
        count_if(intent = 'low')                                   as low_intent_leads,
        round(avg(post_score), 2)                                  as avg_post_score,
        sum(num_comments)                                          as total_comments,
        count(distinct contact_handle)                             as distinct_contacts
    from leads
    group by 1, 2

)

select
    md5(subreddit || '|' || cast(lead_date as varchar))          as lead_day_key,
    subreddit,
    lead_date,
    total_leads,
    qualified_leads,
    high_intent_leads,
    medium_intent_leads,
    low_intent_leads,
    round(qualified_leads * 100.0 / nullif(total_leads, 0), 1)    as qualified_pct,
    avg_post_score,
    total_comments,
    distinct_contacts,m
  postid
from aggregated

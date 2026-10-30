{#
  TEST ONLY: builds <target db>.SNOWPLOW_SIM_<scale>.EVENTS, synthetic Snowplow
  web events shaped like ATOMIC.EVENTS plus the columns the window vars depend
  on (load_tstamp, dvce_created/sent_tstamp, useragent).

  Built-in properties for the tuning skill to find:
  - users: power-law reuse, so heavy users come back day after day
  - sessions: ~20 events, minutes long; 0.2% humans 2.5-4.5 days long; 0.5%
    bots (bot user agent) 4-6 days long with 300-500 events
  - device lateness (dvce_sent - dvce_created), per session: 99.5% seconds,
    0.4% 1-24 hours, 0.1% 2-6 days
  - loader lag (load_tstamp - collector_tstamp), per event: 99% 1-10 minutes,
    0.9% 1-6 hours, 0.1% 8-14 hours

  Events "arrive" by load_tstamp: the compat view filters on var sim_now.
#}
{% macro generate_snowplow_sim(scale, events_per_day, start_date='2026-09-01', days=34, seed=42) %}
  {% set sessions_per_day = (events_per_day / 20) | int %}
  {% set n_users = sessions_per_day * 8 %}
  {% set schema = target.database ~ '.SNOWPLOW_SIM_' ~ scale %}
  {% do run_query('create schema if not exists ' ~ schema) %}
  {% set sql %}
create or replace table {{ schema }}.EVENTS as
with sessions as (
  select
    seq8() as s,
    floor(s / {{ sessions_per_day }}) as day_n,
    dateadd(second, day_n * 86400 + uniform(0, 86399, random({{ seed }})), '{{ start_date }}'::timestamp_ntz) as start_ts,
    floor(power(uniform(0::float, 1::float, random({{ seed + 1 }})), 3) * {{ n_users }}) as user_n,
    uniform(0::float, 1::float, random({{ seed + 2 }})) as r_kind,
    uniform(0.0001::float, 1::float, random({{ seed + 3 }})) as u,
    uniform(0::float, 1::float, random({{ seed + 4 }})) as r_offline,
    case when r_kind < 0.005 then 'bot' when r_kind < 0.007 then 'long' else 'normal' end as kind,
    case kind
      when 'bot' then 86400 * (4 + 2 * u)
      when 'long' then 86400 * (2.5 + 2 * u)
      else least(-ln(u) * 600, 7200)
    end as duration_s,
    case kind
      when 'bot' then 300 + floor(u * 200)
      else least(1 + floor(-ln(uniform(0.0001::float, 1::float, random({{ seed + 5 }}))) * 19), 200)
    end as n_events,
    case
      when r_offline < 0.001 then 86400 * (2 + 4 * uniform(0::float, 1::float, random({{ seed + 6 }})))
      when r_offline < 0.005 then 3600 * (1 + 23 * uniform(0::float, 1::float, random({{ seed + 6 }})))
      else 5 * uniform(0::float, 1::float, random({{ seed + 6 }}))
    end as offline_s
  from table(generator(rowcount => {{ sessions_per_day * days }}))
),

events as (
  select
    s.*,
    f.value::int as k,
    uniform(0::float, 1::float, random({{ seed + 7 }})) as r_event,
    uniform(0::float, 1::float, random({{ seed + 8 }})) as r_lag,
    uniform(0::float, 1::float, random({{ seed + 9 }})) as u_lag,
    dateadd(millisecond, (k / n_events) * duration_s * 1000, start_ts) as event_ts
  from sessions s,
    lateral flatten(input => array_generate_range(0, s.n_events)) f
)

select
  uuid_string() as event_id,
  case when k = 0 or r_event >= 0.70 and r_event < 0.95 then 'page_view'
       when r_event < 0.70 then 'page_ping'
       else 'link_click' end as event_name,
  dateadd(millisecond, offline_s * 1000 + 200, event_ts) as collector_tstamp,
  dateadd(millisecond, 200, event_ts) as derived_tstamp,
  'sim' as app_id,
  'web' as platform,
  null::varchar as user_id,
  'du_' || user_n as domain_userid,
  'nu_' || user_n as network_userid,
  'ds_{{ scale }}_' || s as domain_sessionid,
  1 as domain_sessionidx,
  null::varchar as user_ipaddress,
  'GB' as geo_country,
  null::varchar as geo_region,
  null::varchar as geo_city,
  'https://shop.example.com/p/' || mod(k, 50) as page_url,
  'Product ' || mod(k, 50) as page_title,
  null::varchar as refr_urlhost,
  null::variant as unstruct_event_com_snowplowanalytics_snowplow_link_click_1,
  null::variant as unstruct_event_com_snowplowanalytics_snowplow_application_error_1,
  null::variant as unstruct_event_com_snowplowanalytics_snowplow_consent_preferences_1,
  'com.snowplowanalytics.snowplow' as event_vendor,
  dateadd(second,
    case when r_lag < 0.009 then 3600 * (1 + 5 * u_lag)
         when r_lag < 0.010 then 3600 * (8 + 6 * u_lag)
         else 60 * (1 + 9 * u_lag) end,
    collector_tstamp) as load_tstamp,
  case when kind = 'bot'
    then 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    else 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
  end as useragent,
  event_ts as dvce_created_tstamp,
  dateadd(millisecond, offline_s * 1000, event_ts) as dvce_sent_tstamp
from events
order by collector_tstamp
  {% endset %}
  {% do run_query(sql) %}
  {% do log('generated ' ~ schema ~ '.EVENTS', info=True) %}
{% endmacro %}

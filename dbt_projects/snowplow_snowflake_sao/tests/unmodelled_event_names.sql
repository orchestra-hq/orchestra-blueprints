-- Flags event_names present in the events table that no normalized model covers.
--
-- normalize_config.json lists the events to model; anything Snowplow starts
-- emitting that is not in that list lands in ATOMIC.EVENTS, gets no model, and
-- never reaches the dashboard — with no error anywhere. This compares the two
-- relations that already exist rather than hardcoding the list, so adding an
-- event to normalize_config.json and regenerating is enough to silence it.
--
-- severity: warn, like the other freshness checks here — an error would fail
-- dbt build, and the Lightdash refresh task is gated on that task succeeding.
--
-- Scope: base_events_this_run only holds the current run's window, so this
-- reports drift as new data arrives rather than auditing history.
{{ config(severity = 'warn') }}

select
    event_name,
    count(*) as events
from {{ ref('snowplow_normalize_base_events_this_run') }}
where event_name not in (
    select distinct event_name
    from {{ ref('snowplow_events_normalized') }}
)
group by 1

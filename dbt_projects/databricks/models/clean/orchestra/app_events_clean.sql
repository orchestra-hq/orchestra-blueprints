select 

  a.Day,
  SHA2(cast(a.Day as STRING), 256) _pk

 from {{ref('daily_calendar')}} a
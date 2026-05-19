select 

  a.Day,
  sha2(cast(a.Day as STRING), 256) _pk

 from {{ref('daily_calendar')}} a
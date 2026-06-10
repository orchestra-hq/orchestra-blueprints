select 

  a.Day,
  HASHBYTES('SHA2_256', cast(a.Day as STRING)) _pk

 from {{ref('daily_calendar')}} a
select 

  a.Day,
  HASHBYTES('SHA2_256', cast(a.Day as NVARCHAR(255))) _pk

 from {{ref('daily_calendar')}} a
select

*



from {{source('base', 'hubspot_contacts_raw')}}
where 1=1

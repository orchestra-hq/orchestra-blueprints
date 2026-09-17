select *
from (
    values
        (101, 'Acme Ltd', to_date('2026-07-02')),
        (102, 'Bramble & Co', to_date('2026-07-11')),
        (103, 'Corvid Data', to_date('2026-07-19')),
        (104, 'Dunlin Retail', to_date('2026-07-28')),
        (105, 'Everly Foods', to_date('2026-08-01'))
) as customers (customer_id, customer_name, signup_date)

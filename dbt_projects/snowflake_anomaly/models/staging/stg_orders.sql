select *
from (
    values
        (1, 101, to_date('2026-08-01'), 'completed', 120.50),
        (2, 102, to_date('2026-08-01'), 'completed', 75.00),
        (3, 101, to_date('2026-08-02'), 'returned', 120.50),
        (4, 103, to_date('2026-08-02'), 'completed', 240.00),
        (5, 104, to_date('2026-08-03'), 'pending', 18.99),
        (6, 102, to_date('2026-08-03'), 'completed', 64.25),
        (7, 105, to_date('2026-08-04'), 'completed', 310.10),
        (8, 103, to_date('2026-08-04'), 'pending', 45.00)
) as orders (order_id, customer_id, order_date, status, amount)

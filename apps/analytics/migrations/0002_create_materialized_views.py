"""
Migration: Barcha Materialized View larni yaratish
apps/analytics/migrations/0001_create_materialized_views.py
"""
from django.db import migrations


# ── SQL: CREATE ───────────────────────────────────────────────────────────────

CREATE_DAILY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_summary_mv AS
SELECT
    DATE(s.created_at)                              AS date,
    COALESCE(SUM(s.total_amount),          0)       AS total_sales,
    COALESCE(SUM(si.expense),              0)       AS total_expense,
    COALESCE(SUM(p.day_payments),          0)       AS total_payments,
    COALESCE(SUM(s.total_amount), 0)
        - COALESCE(SUM(si.expense), 0)              AS total_profit
FROM products_sale s
LEFT JOIN (
    SELECT sale_id, SUM(quantity * cost_price_at_sale) AS expense
    FROM products_saleitem
    GROUP BY sale_id
) si ON si.sale_id = s.id
LEFT JOIN (
    SELECT DATE(created_at) AS day, SUM(amount) AS day_payments
    FROM products_payment
    GROUP BY DATE(created_at)
) p ON p.day = DATE(s.created_at)
GROUP BY DATE(s.created_at)
WITH DATA;
"""

CREATE_DAILY_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS dashboard_summary_mv_date_idx
    ON dashboard_summary_mv (date);
"""

# ─────────────────────────────────────────────────────────────────────────────

CREATE_TOP_PRODUCTS = """
CREATE MATERIALIZED VIEW IF NOT EXISTS top_products_mv AS
SELECT
    p.id                                            AS product_id,
    p.name                                          AS product_name,
    COALESCE(c.name, 'Kategoriyasiz')               AS category_name,
    COALESCE(SUM(si.quantity),              0)      AS total_sold,
    COALESCE(SUM(si.quantity * si.price_at_sale),   0) AS total_revenue,
    COALESCE(SUM(si.quantity * (si.price_at_sale - si.cost_price_at_sale)), 0) AS total_profit
FROM products_product p
LEFT JOIN products_saleitem si ON si.product_id = p.id
LEFT JOIN products_category c  ON c.id = p.category_id
GROUP BY p.id, p.name, c.name
WITH DATA;
"""

CREATE_TOP_PRODUCTS_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS top_products_mv_product_id_idx
    ON top_products_mv (product_id);
"""

# ─────────────────────────────────────────────────────────────────────────────

CREATE_MONTHLY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_summary_mv AS
SELECT
    DATE_TRUNC('month', s.created_at)::date         AS month,
    COALESCE(SUM(s.total_amount),          0)       AS total_sales,
    COALESCE(SUM(si.expense),              0)       AS total_expense,
    COALESCE(SUM(p.month_payments),        0)       AS total_payments,
    COALESCE(SUM(s.total_amount), 0)
        - COALESCE(SUM(si.expense), 0)              AS total_profit
FROM products_sale s
LEFT JOIN (
    SELECT sale_id, SUM(quantity * cost_price_at_sale) AS expense
    FROM products_saleitem
    GROUP BY sale_id
) si ON si.sale_id = s.id
LEFT JOIN (
    SELECT DATE_TRUNC('month', created_at)::date AS month, SUM(amount) AS month_payments
    FROM products_payment
    GROUP BY DATE_TRUNC('month', created_at)
) p ON p.month = DATE_TRUNC('month', s.created_at)::date
GROUP BY DATE_TRUNC('month', s.created_at)
WITH DATA;
"""

CREATE_MONTHLY_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS monthly_summary_mv_month_idx
    ON monthly_summary_mv (month);
"""

# ─────────────────────────────────────────────────────────────────────────────

CREATE_YEARLY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS yearly_summary_mv AS
SELECT
    EXTRACT(YEAR FROM s.created_at)::int            AS year,
    COALESCE(SUM(s.total_amount),          0)       AS total_sales,
    COALESCE(SUM(si.expense),              0)       AS total_expense,
    COALESCE(SUM(p.year_payments),         0)       AS total_payments,
    COALESCE(SUM(s.total_amount), 0)
        - COALESCE(SUM(si.expense), 0)              AS total_profit
FROM products_sale s
LEFT JOIN (
    SELECT sale_id, SUM(quantity * cost_price_at_sale) AS expense
    FROM products_saleitem
    GROUP BY sale_id
) si ON si.sale_id = s.id
LEFT JOIN (
    SELECT EXTRACT(YEAR FROM created_at)::int AS yr, SUM(amount) AS year_payments
    FROM products_payment
    GROUP BY EXTRACT(YEAR FROM created_at)
) p ON p.yr = EXTRACT(YEAR FROM s.created_at)::int
GROUP BY EXTRACT(YEAR FROM s.created_at)
WITH DATA;
"""

CREATE_YEARLY_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS yearly_summary_mv_year_idx
    ON yearly_summary_mv (year);
"""

# ── SQL: DROP ────────────────────────────────────────────────────────────────

DROP_ALL = """
DROP MATERIALIZED VIEW IF EXISTS yearly_summary_mv;
DROP MATERIALIZED VIEW IF EXISTS monthly_summary_mv;
DROP MATERIALIZED VIEW IF EXISTS top_products_mv;
DROP MATERIALIZED VIEW IF EXISTS dashboard_summary_mv;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                CREATE_DAILY,
                CREATE_DAILY_INDEX,
                CREATE_TOP_PRODUCTS,
                CREATE_TOP_PRODUCTS_INDEX,
                CREATE_MONTHLY,
                CREATE_MONTHLY_INDEX,
                CREATE_YEARLY,
                CREATE_YEARLY_INDEX,
            ],
            reverse_sql=DROP_ALL,
        ),
    ]
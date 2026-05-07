from django.db import connection
from django.core.cache import cache


class DashboardService:
    @staticmethod
    def get_dashboard_data():
        cache_key = "dashboard_full_data"
        data = cache.get(cache_key)
        if data is None:
            data = {
                "year": DashboardService._get_year_stats(),
                "chart": {
                    "weekly": DashboardService._get_weekly_chart(),
                    "monthly": DashboardService._get_monthly_chart(),
                    "yearly": DashboardService._get_yearly_chart(),
                },
                "top_products": DashboardService._get_top_products(),
            }
            cache.set(cache_key, data, timeout=300)
        return data

    @staticmethod
    def _get_year_stats():
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(SUM(total_sales),0), COALESCE(SUM(total_expense),0), COALESCE(SUM(total_payments),0), COALESCE(SUM(total_profit),0) FROM dashboard_summary_mv WHERE date >= date_trunc('year', CURRENT_DATE);")
            row = cursor.fetchone()
        return {
            "sale": float(row[0]), "expense": float(row[1]),
            "payment": float(row[2]), "profit": float(row[3])
        }
    
    @staticmethod
    def _get_weekly_chart():

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    TO_CHAR(date, 'DD-MM'),
                    total_sales,
                    total_expense,
                    total_payments,
                    total_profit

                FROM dashboard_summary_mv

                WHERE date >= CURRENT_DATE - INTERVAL '7 days'

                ORDER BY date ASC;
            """)

            rows = cursor.fetchall()

        return {
            "labels": [r[0] for r in rows],
            "sales": [float(r[1]) for r in rows],
            "expenses": [float(r[2]) for r in rows],
            "payments": [float(r[3]) for r in rows],
            "profits": [float(r[4]) for r in rows],
        }
    
    @staticmethod
    def _get_monthly_chart():
        with connection.cursor() as cursor:
            cursor.execute("SELECT TO_CHAR(month,'MM-YYYY'), total_sales, total_expense, total_payments, total_profit FROM monthly_summary_mv WHERE month >= date_trunc('year', CURRENT_DATE) ORDER BY month;")
            rows = cursor.fetchall()
        return {
            "labels": [r[0] for r in rows],
            "sales": [float(r[1]) for r in rows],
            "expenses": [float(r[2]) for r in rows],
            "payments": [float(r[3]) for r in rows],
            "profits": [float(r[4]) for r in rows],
        }

    @staticmethod
    def _get_yearly_chart():
        with connection.cursor() as cursor:
            cursor.execute("SELECT year::text, total_sales, total_expense, total_payments, total_profit FROM yearly_summary_mv ORDER BY year DESC LIMIT 5;")
            rows = cursor.fetchall()
        return {
            "labels": [r[0] for r in rows],
            "sales": [float(r[1]) for r in rows],
            "expenses": [float(r[2]) for r in rows],
            "payments": [float(r[3]) for r in rows],
            "profits": [float(r[4]) for r in rows],
        }

    @staticmethod
    def _get_top_products():
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    product_name, 
                    category_name, 
                    total_sold, 
                    total_revenue, 
                    total_profit 
                FROM top_products_mv 
                ORDER BY total_sold DESC 
                LIMIT 8;
            """)
            rows = cursor.fetchall()

        if not rows:
            return []  # bo'sh bo'lsa bo'sh qaytaradi

        return [
            {
                "name": row[0],
                "category": row[1],
                "sold": int(row[2]),
                "revenue": float(row[3]),
                "profit": float(row[4]),
            }
            for row in rows
        ]
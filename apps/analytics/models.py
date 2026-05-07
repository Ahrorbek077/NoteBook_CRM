from django.db import models
from django.db.models import F, Sum, Value
from django.utils import timezone

class DashboardSummary(models.Model):
    """Materialized View uchun model (managed=False)"""
    date = models.DateField(primary_key=True)   # yoki Composite PK
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Top products uchun alohida view qilamiz (keyinroq)
    class Meta:
        managed = False
        db_table = 'dashboard_summary_mv'

class TopProductSummary(models.Model):
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=200)
    category_name = models.CharField(max_length=100)
    total_sold = models.PositiveIntegerField()
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'top_products_mv'

class WeeklySummary(models.Model):
    week_start = models.DateField(primary_key=True)
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        managed = False
        db_table = 'weekly_summary_mv'

class MonthlySummary(models.Model):
    month = models.DateField(primary_key=True)  # oy boshlanishi
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        managed = False
        db_table = 'monthly_summary_mv'

class YearlySummary(models.Model):
    """Yillik summary uchun MV"""
    year = models.IntegerField(primary_key=True)
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        managed = False
        db_table = 'yearly_summary_mv'
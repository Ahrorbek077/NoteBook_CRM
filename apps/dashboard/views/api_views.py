from django.http import JsonResponse
from django.db.models import Sum, F
from django.utils.timezone import now, timedelta
from django.core.cache import cache
from django.utils.timezone import now
from apps.products.models import Sale, SaleItem, Payment
from apps.services.dashboard_service import DashboardService

# ====== Bular ishlamaydi hozircha kichik hisob dashboardi uchun Pastidagi funksiya ishlaydi========= 
def get_year_stats():
    today = now().date()
    year_start = today.replace(month=1, day=1)

    total_sale = Sale.objects.filter(created_at__date__gte=year_start).aggregate(
        s=Sum("total_amount")
    )["s"] or 0

    total_expense = SaleItem.objects.filter(
        sale__created_at__date__gte=year_start
    ).aggregate(
        e=Sum(F("quantity") * F("cost_price_at_sale"))
    )["e"] or 0

    total_payment = Payment.objects.filter(created_at__date__gte=year_start).aggregate(
        p=Sum("amount")
    )["p"] or 0

    return {
        "sale": float(total_sale),
        "expense": float(total_expense),
        "payment": float(total_payment),
        "profit": float(total_sale - total_expense),
    }

# ====================================================
def get_weekly_chart():
    today = now().date()
    week_ago = today - timedelta(days=6)

    labels = []
    sales = []
    expenses = []
    payments = []

    for i in range(7):
        d = week_ago + timedelta(days=i)
        labels.append(d.strftime("%d-%m"))

        sale = Sale.objects.filter(created_at__date=d).aggregate(s=Sum("total_amount"))["s"] or 0
        expense = SaleItem.objects.filter(sale__created_at__date=d).aggregate(
            e=Sum(F("quantity") * F("cost_price_at_sale"))
        )["e"] or 0
        payment = Payment.objects.filter(created_at__date=d).aggregate(p=Sum("amount"))["p"] or 0

        sales.append(float(sale))
        expenses.append(float(expense))
        payments.append(float(payment))

    profits = [s - e for s, e in zip(sales, expenses)]

    return {
        "labels": labels,
        "profits": profits,
        "expenses": expenses,
        "payments": payments
    }

# ============================================
def get_monthly_chart():
    labels = []
    sales = []
    expenses = []
    payments = []

    today = now().date()
    year = today.year

    for month in range(1, 13):
        labels.append(f"{month}-oy")

        sale = Sale.objects.filter(created_at__year=year, created_at__month=month).aggregate(
            s=Sum("total_amount")
        )["s"] or 0

        expense = SaleItem.objects.filter(
            sale__created_at__year=year,
            sale__created_at__month=month
        ).aggregate(
            e=Sum(F("quantity") * F("cost_price_at_sale"))
        )["e"] or 0

        payment = Payment.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).aggregate(p=Sum("amount"))["p"] or 0

        sales.append(float(sale))
        expenses.append(float(expense))
        payments.append(float(payment))

    profits = [s - e for s, e in zip(sales, expenses)]

    return {
        "labels": labels,
        "profits": profits,
        "expenses": expenses,
        "payments": payments
    }

# ========================================
def get_yearly_chart():
    today = now().date()
    current_year = today.year

    labels = []
    sales = []
    expenses = []
    payments = []

    for y in range(current_year - 4, current_year + 1):
        labels.append(str(y))

        sale = Sale.objects.filter(created_at__year=y).aggregate(
            s=Sum("total_amount")
        )["s"] or 0

        expense = SaleItem.objects.filter(sale__created_at__year=y).aggregate(
            e=Sum(F("quantity") * F("cost_price_at_sale"))
        )["e"] or 0

        payment = Payment.objects.filter(created_at__year=y).aggregate(
            p=Sum("amount")
        )["p"] or 0

        sales.append(float(sale))
        expenses.append(float(expense))
        payments.append(float(payment))

    profits = [s - e for s, e in zip(sales, expenses)]

    return {
        "labels": labels,
        "profits": profits,
        "expenses": expenses,
        "payments": payments
    }

# =========================================
def get_top_products():
    qs = (
        SaleItem.objects.values("product__name", "product__category__name", "price_at_sale")
        .annotate(total=Sum("quantity"))
        .order_by("-total")[:5]
    )

    return [
        {
            "name": x["product__name"],
            "category": x["product__category__name"],
            "price": float(x["price_at_sale"]),
            "sold": x["total"],
        }
        for x in qs
    ]


def dashboard_api(request):
    try:
        data = DashboardService.get_dashboard_data()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
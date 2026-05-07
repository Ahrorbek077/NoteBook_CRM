# apps/analytics/tasks.py
from celery import shared_task
from django.db import connection
import logging

logger = logging.getLogger(__name__)

# MV nomi migratsiya bilan mos bo'lishi SHART
MATERIALIZED_VIEWS = [
    'dashboard_summary_mv',      # daily — DashboardService ishlatadi
    'top_products_mv',
    'monthly_summary_mv',
    'yearly_summary_mv',
]


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,       # 5s, 10s, 20s …
    max_retries=3,
    name='analytics.refresh_materialized_views',
)
def refresh_materialized_views(self):
    """
    Barcha MV larni CONCURRENTLY yangilash.
    CONCURRENTLY ishlashi uchun har bir MV da UNIQUE INDEX bo'lishi kerak
    (migration da yaratilgan).
    """
    errors = []

    with connection.cursor() as cursor:
        for view in MATERIALIZED_VIEWS:
            try:
                cursor.execute(
                    f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view};"
                )
                logger.info("✅ %s yangilandi", view)
            except Exception as exc:
                logger.error("❌ %s xatolik: %s", view, exc)
                errors.append(f"{view}: {exc}")

    if errors:
        raise RuntimeError("MV refresh xatoliklari:\n" + "\n".join(errors))

    return "OK"
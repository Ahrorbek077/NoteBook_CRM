# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.products.models import (
    Product, Sale, SaleReturn, Payment, PaymentRefund,
    Client, StockBatch, StockAdjustment, ActivityLog
)

# ============ PRODUCT ============
@receiver(post_save, sender=Product)
def log_product_save(sender, instance, created, **kwargs):
    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        action_type='product_create' if created else 'product_update',
        description=f"{'Yangi mahsulot' if created else 'Mahsulot yangilandi'}: {instance.name}",
        extra_data={
            "product_id": instance.id,
            "name":       instance.name,
            "price":      str(instance.price),
            "stock":      instance.stock,
        }
    )

@receiver(post_delete, sender=Product)
def log_product_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        action_type='product_delete',
        description=f"Mahsulot o'chirildi: {instance.name}",
        extra_data={"product_id": instance.id, "name": instance.name}
    )

# ============ CLIENT ============
@receiver(post_save, sender=Client)
def log_client_save(sender, instance, created, **kwargs):
    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        action_type='client_create' if created else 'client_update',
        description=f"{'Yangi mijoz' if created else 'Mijoz yangilandi'}: {instance.name}",
        extra_data={
            "client_id": instance.id,
            "name":      instance.name,
            "phone":     instance.phone,
            "region":    instance.region.name if instance.region else None,
        }
    )

@receiver(post_delete, sender=Client)
def log_client_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        action_type='client_delete',
        description=f"Mijoz o'chirildi: {instance.name}",
        extra_data={"client_id": instance.id, "name": instance.name}
    )

# ============ STOCK BATCH ============
@receiver(post_save, sender=StockBatch)
def log_stock_add(sender, instance, created, **kwargs):
    if not created:
        return
    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        action_type='stock_add',
        description=f"{instance.product.name} — {instance.quantity_received} ta kirim",
        extra_data={
            "batch_id":   instance.id,
            "product_id": instance.product_id,
            "product":    instance.product.name,
            "quantity":   instance.quantity_received,
            "cost_price": str(instance.cost_price),
            "total_cost": str(instance.cost_price * instance.quantity_received),
        }
    )

# ============ STOCK ADJUSTMENT ============
@receiver(post_save, sender=StockAdjustment)
def log_stock_adjust(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.adjustment_type == 'return':
        return  # return larni sale_return signal yozadi

    batch = instance.batch
    ActivityLog.objects.create(
        user=instance.user,
        action_type='stock_adjust',
        description=f"{batch.product.name} — batch #{batch.id} tuzatildi",
        extra_data={
            "batch_id":       batch.id,
            "product_id":     batch.product_id,
            "product":        batch.product.name,
            "adjustment_type": instance.adjustment_type,
            "quantity_change": instance.quantity_change,
            "new_cost_price":  str(instance.new_cost_price) if instance.new_cost_price else None,
            "reason":          instance.reason,
        }
    )

# ============ SALE ============

# ============ PAYMENT ============
@receiver(post_save, sender=Payment)
def log_payment_created(sender, instance, created, **kwargs):
    if not created:
        return
    ActivityLog.objects.create(
        user=instance.user,
        action_type='payment',
        description=f"{instance.client.name} — {instance.amount:,.0f} so'm to'lov",
        extra_data={
            "payment_id":  instance.id,
            "client_id":   instance.client_id,
            "client_name": instance.client.name,
            "amount":      str(instance.amount),
            "note":        instance.note or '',
        }
    )

# ============ PAYMENT REFUND ============
@receiver(post_save, sender=PaymentRefund)
def log_payment_refund(sender, instance, created, **kwargs):
    if not created:
        return
    ActivityLog.objects.create(
        user=instance.user,
        action_type='payment_refund',
        description=f"{instance.payment.client.name} — {instance.amount:,.0f} so'm to'lov qaytarildi",
        extra_data={
            "refund_id":   instance.id,
            "payment_id":  instance.payment_id,
            "client_id":   instance.payment.client_id,
            "client_name": instance.payment.client.name,
            "amount":      str(instance.amount),
            "reason":      instance.reason or '',
        }
    )
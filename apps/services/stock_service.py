from decimal import Decimal
from django.db import transaction
from django.db.models import F
from apps.products.models import Product, StockBatch, StockAdjustment


class StockService:

    @staticmethod
    def add_stock(product: Product, quantity: int, cost_price: Decimal):
        if quantity <= 0 or cost_price <= 0:
            raise ValueError("Miqdor va narx musbat bo'lishi kerak")

        if not product.is_active:
            raise ValueError(f"{product.name} mahsuloti faol emas!")

        with transaction.atomic():
            batch = StockBatch.objects.create(
                product=product,
                quantity_received=quantity,
                remaining_quantity=quantity,
                cost_price=cost_price
            )

            product.stock = F('stock') + quantity
            product.save(update_fields=['stock'])

            return batch

    # 🔒 IMMUTABLE SAFE ADJUSTMENT
    @staticmethod
    def adjust_stock(batch: StockBatch, quantity_change: int = 0,
                     new_cost_price: Decimal = None, user=None, reason=""):

        # ❗ faqat untouched batchga ruxsat
        if batch.remaining_quantity != batch.quantity_received:
            raise ValueError("Sarflangan batchni o‘zgartirib bo‘lmaydi")

        with transaction.atomic():

            if new_cost_price and quantity_change == 0:
                adjustment_type = 'price_change'
            elif quantity_change > 0:
                adjustment_type = 'increase'
            elif quantity_change < 0:
                adjustment_type = 'decrease'
            else:
                adjustment_type = 'correction'

            adjustment = StockAdjustment.objects.create(
                batch=batch,
                user=user,
                adjustment_type=adjustment_type,
                quantity_change=quantity_change,
                new_cost_price=new_cost_price,
                reason=reason
            )

            # quantity change
            if quantity_change != 0:
                if batch.remaining_quantity + quantity_change < 0:
                    raise ValueError("Manfiy stock bo‘lib qolyapti")

                batch.remaining_quantity += quantity_change
                batch.quantity_received += quantity_change
                batch.save(update_fields=['remaining_quantity', 'quantity_received'])

                product = batch.product
                product.stock = F('stock') + quantity_change
                product.save(update_fields=['stock'])

            # price change
            if new_cost_price and new_cost_price > 0:
                batch.cost_price = new_cost_price
                batch.save(update_fields=['cost_price'])

            return adjustment

    # 🔥 FIFO WITH BATCH SPLIT
    @staticmethod
    def consume_fifo_stock_detailed(product: Product, quantity: int):
        if quantity <= 0:
            return []

        if not product.is_active:
            raise ValueError(f"{product.name} mahsuloti faol emas!")

        with transaction.atomic():
            remaining = quantity
            result = []

            batches = StockBatch.objects.select_for_update().filter(
                product=product,
                remaining_quantity__gt=0
            ).order_by('created_at')

            for batch in batches:
                if remaining <= 0:
                    break

                consume = min(remaining, batch.remaining_quantity)

                result.append({
                    "batch": batch,
                    "quantity": consume,
                    "cost_price": batch.cost_price
                })

                batch.remaining_quantity -= consume
                batch.save(update_fields=['remaining_quantity'])

                remaining -= consume

            if remaining > 0:
                raise ValueError(f"{product.name} yetarli emas!")

            product.stock = F('stock') - quantity
            product.save(update_fields=['stock'])

            return result

    @staticmethod
    def return_to_original_batch(batch: StockBatch, quantity: int, user=None, reason=""):
        if quantity <= 0:
            return

        with transaction.atomic():

            # ❗ over-returnni oldini olish
            if batch.remaining_quantity + quantity > batch.quantity_received:
                raise ValueError("Ortiqcha return bo‘lyapti")

            batch.remaining_quantity += quantity
            batch.save(update_fields=['remaining_quantity'])

            product = batch.product
            product.stock = F('stock') + quantity
            product.save(update_fields=['stock'])

            StockAdjustment.objects.create(
                batch=batch,
                user=user,
                adjustment_type='return',          # ← 'increase' emas
                quantity_change=quantity,
                reason=reason or "Return orqali qo‘shildi"
            )
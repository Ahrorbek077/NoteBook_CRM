from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from apps.products.models import Product, Sale, SaleItem, Client, SaleReturn, SaleReturnItem, ActivityLog
from apps.analytics.tasks import refresh_materialized_views
from apps.services.stock_service import StockService
from django.db.transaction import on_commit


class SaleService:

    @staticmethod
    def create_sale_from_cart(client: Client, cart_items: list, user=None):

        if not client.is_active:
            raise ValueError(f"Mijoz {client.name} faol emas!")

        with transaction.atomic(savepoint=False):

            total_amount = Decimal('0')
            sale_items = []

            product_ids = [item['product_id'] for item in cart_items]

            products = {
                p.id: p
                for p in Product.objects.select_for_update().filter(
                    id__in=product_ids,
                    is_active=True
                )
            }

            for item in cart_items:
                product = products.get(item['product_id'])

                if not product:
                    raise ValueError("Product topilmadi")

                qty = item['quantity']

                if product.stock < qty:
                    raise ValueError(f"{product.name} yetarli emas!")

                # FIFO SPLIT
                fifo_items = StockService.consume_fifo_stock_detailed(product, qty)

                for f in fifo_items:
                    subtotal = product.price * f["quantity"]
                    total_amount += subtotal

                    sale_items.append(SaleItem(
                        product=product,
                        batch=f["batch"],
                        quantity=f["quantity"],
                        price_at_sale=product.price,
                        cost_price_at_sale=f["cost_price"],
                    ))

            sale = Sale.objects.create(
                client=client,
                user=user,
                total_amount=total_amount
            )
            
            for si in sale_items:
                si.sale = sale

            SaleItem.objects.bulk_create(sale_items, batch_size=500)

            items_data = [
                {
                    "product":  si.product.name,
                    "quantity": si.quantity,
                    "price":    str(si.price_at_sale),
                    "subtotal": str(si.price_at_sale * si.quantity),
                }

                for si in sale_items
            ]

            ActivityLog.objects.create(
                user=user,
                action_type='sale',
                description=f"{client.name} — {total_amount:,.0f} so'm sotuv",
                extra_data={
                    "sale_id":      sale.id,
                    "client_id":    client.id,
                    "client_name":  client.name,
                    "total_amount": str(total_amount),
                    "items":        items_data,
                }
            )


            SaleService._update_client_balance_atomic(client, total_amount)

            cache.delete('dashboard_full_data')

            on_commit(
                lambda: refresh_materialized_views.delay()
            )

            return sale

    @staticmethod
    def process_return(sale: Sale, return_data: list, user=None, reason=""):
        with transaction.atomic(savepoint=True):
            sale_return = SaleReturn.objects.create(
                sale=sale,
                user=user,
                reason=reason
            )

            returned_items_data = []
            returned_amount = Decimal('0')

            for item_data in return_data:
                sale_item = SaleItem.objects.select_for_update().get(
                    id=item_data['sale_item_id'],
                    sale=sale
                )

                qty = item_data['quantity']

                print("CHECK:", sale_item.id, qty, sale_item.get_remaining_quantity())

                if qty <= 0:
                    raise ValueError("Qaytarish miqdori musbat bo‘lishi kerak")

                if qty > sale_item.get_remaining_quantity():
                    raise ValueError("Qaytarish miqdori noto‘g‘ri")

                if not sale_item.batch:
                    raise ValueError("Batch topilmadi")
                
                # 🔥 HAR DOIM batch bor endi
                StockService.return_to_original_batch(
                    batch=sale_item.batch,
                    quantity=qty,
                    user=user,
                    reason=reason
                )

                sale_item.returned_quantity += qty
                sale_item.save(update_fields=['returned_quantity'])

                returned_amount += sale_item.price_at_sale * qty

                SaleReturnItem.objects.create(
                    sale_return=sale_return,
                    sale_item=sale_item,
                    returned_quantity=qty,
                    returned_to_batch=sale_item.batch
                )

                # ✅ items_data to'pla
                returned_items_data.append({
                    "product":  sale_item.product.name,
                    "quantity": qty,
                    "price":    str(sale_item.price_at_sale),
                    "subtotal": str(qty * sale_item.price_at_sale),
                })

            # ✅ Hamma narsa tayyor — log yoz
            ActivityLog.objects.create(
                user=user,
                action_type='sale_return',
                description=f"{sale.client.name} — {returned_amount:,.0f} so'm qaytarildi",
                extra_data={
                    "return_id":   sale_return.id,
                    "sale_id":     sale.id,
                    "client_id":   sale.client_id,
                    "client_name": sale.client.name,
                    "total":       str(returned_amount),
                    "reason":      reason,
                    "items":       returned_items_data,
                }
            )

            # 🔥 CLIENT BALANCE NI QAYTARISH
            SaleService._update_client_balance_for_return(sale.client, returned_amount)
            
            if all(item.returned_quantity >= item.quantity for item in sale.items.all()):
                sale.cancel(cancelled_by=user)

            return sale_return
        
    # 🔥 YANGI METOD — Return uchun balansni to‘g‘rilash
    @staticmethod
    def _update_client_balance_for_return(client: Client, amount: Decimal):
        if amount <= 0:
            return

        if not client.is_active:
            raise ValueError("Mijoz faol emas!")

        client = Client.objects.select_for_update().get(pk=client.pk)

        if client.total_debt >= amount:
            client.total_debt -= amount
        else:
            remaining = amount - client.total_debt
            client.total_debt = Decimal('0')
            client.advance_balance += remaining

        client.save(update_fields=['total_debt', 'advance_balance'])

    @staticmethod
    def _update_client_balance_atomic(client: Client, amount: Decimal):
        if not client.is_active:
            raise ValueError("Mijoz faol emas!")

        client = Client.objects.select_for_update().get(pk=client.pk)

        if client.advance_balance >= amount:
            client.advance_balance -= amount
        else:
            remaining = amount - client.advance_balance
            client.advance_balance = Decimal('0')
            client.total_debt += remaining
 
        client.save(update_fields=['total_debt', 'advance_balance'])

    @staticmethod
    def full_cancel_sale(sale, cancelled_by=None, reason=""):
        with transaction.atomic():
            remaining_items = [
                {
                    'sale_item_id': item.id,
                    'quantity': item.get_remaining_quantity()
                }
                for item in sale.items.all()
                if item.get_remaining_quantity() > 0
            ]

            if not remaining_items:
                return  # allaqachon return bo‘lgan

            # 🔥 faqat process_return
            SaleService.process_return(
                sale=sale,
                return_data=remaining_items,
                user=cancelled_by,
                reason=reason or "Full Cancel"
            )
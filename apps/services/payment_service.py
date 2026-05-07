from decimal import Decimal
from django.db import transaction
from django.core.cache import cache
from apps.products.models import Client, Payment, PaymentRefund
from apps.analytics.tasks import refresh_materialized_views
from django.db.transaction import on_commit

class PaymentService:
    
    @staticmethod
    def create_payment(client: Client, amount: Decimal, user=None, note=""):
        if amount <= 0:
            raise ValueError("To‘lov summasi musbat bo‘lishi kerak")

        with transaction.atomic(savepoint=False):
            # Mijozni lock qilish
            client = Client.objects.select_for_update().get(pk=client.pk)

            Payment.objects.create(
                client=client,
                amount=amount,
                user=user,
                note=note
            )

            if client.total_debt >= amount:
                client.total_debt -= amount
            else:
                remaining = amount - client.total_debt
                client.total_debt = Decimal('0')
                client.advance_balance += remaining

            client.save(update_fields=['total_debt', 'advance_balance'])
            
            # Cache ni tozalash
            cache.delete('dashboard_full_data')

            on_commit(
                lambda: refresh_materialized_views.delay()
            )

            return

    @staticmethod
    def refund_payment(payment: Payment, amount: Decimal, user=None, reason=""):
        if amount <= 0:
            raise ValueError("Qaytarish summasi musbat bo'lishi kerak")

        if amount > payment.get_remaining_amount():
            raise ValueError(
                f"Maksimal qaytarish: {payment.get_remaining_amount()} so'm"
            )

        with transaction.atomic():
            # Paymentni lock qilish
            payment = Payment.objects.select_for_update().get(pk=payment.pk)
            client = Client.objects.select_for_update().get(pk=payment.client.pk)

            # Refund yozuvi
            PaymentRefund.objects.create(
                payment=payment,
                amount=amount,
                user=user,
                reason=reason
            )

            # Payment da refunded_amount yangilash
            payment.refunded_amount += amount
            payment.save(update_fields=['refunded_amount'])

            if client.advance_balance >= amount:
                client.advance_balance -= amount
            else:
                remaining = amount - client.advance_balance
                client.advance_balance = Decimal('0')
                client.total_debt += remaining

            client.save(update_fields=['total_debt', 'advance_balance'])


            cache.delete('dashboard_full_data')

            on_commit(
                lambda: refresh_materialized_views.delay()
            )

            return payment    
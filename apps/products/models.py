from django.db import models
from django.conf import settings
from django_resized import ResizedImageField
from django.utils.text import slugify
from django.db.models import Sum
from decimal import Decimal
from apps.products.managers import SoftDeleteManager, NotCancelledManager
from django.utils import timezone


# ====================== CATEGORY ======================
class Category(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    objects = SoftDeleteManager()           # faqat active
    all_objects = models.Manager()          # barchasi (admin uchun)
    
# ====================== PRODUCT ======================
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey("Category", on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(max_length=256, unique=True, blank=True)
    image = ResizedImageField(size=[756, 741], crop=['middle', 'center'], upload_to='products/%Y/%m')
    
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Sotuv narxi")
    stock = models.PositiveIntegerField(default=0, editable=False)

    is_active = models.BooleanField(default=True)      # ← Soft Delete

    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.slug or not self.pk:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.all_objects.filter(slug=slug).exists():   # all_objects bilan tekshirish
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
    
    objects = SoftDeleteManager()           # faqat active
    all_objects = models.Manager()          # barchasi (admin uchun)

# ====================== CLIENT ======================
class Client(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    region  = models.ForeignKey(                          # ← yangi
        Region,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clients'
    )
    total_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0) # Oldindan to'lov balansi
    
    is_active = models.BooleanField(default=True)      # ← Soft Delete

    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name

    """Million savdo bo'lsa ham to'g'ri hisoblaydi (audit uchun)"""
    def recalculate_balances(self):
        total_sales = self.sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        total_payments = self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        debt = total_sales - total_payments

        self.total_debt = max(debt, Decimal('0'))
        self.advance_balance = max(-debt, Decimal('0'))

        self.save(update_fields=['total_debt', 'advance_balance'])
        return self.total_debt, self.advance_balance

# ====================== STOCKBATCH ======================
class StockBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_batches')
    quantity_received = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)  
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    def soft_delete(self, user=None, reason=""):
        # Faqat bo'sh batchni o'chirish mumkin
        if self.remaining_quantity > 0:
            raise ValueError(
                f"Batchda {self.remaining_quantity} ta qoldiq bor — o'chirib bo'lmaydi"
            )
        self.is_active = False
        self.save(update_fields=['is_active'])
        
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.remaining_quantity}/{self.quantity_received} ta @ {self.cost_price}"

# ====================== STOCK ADJUSTMENT (Admin tuzatish uchun) ======================
class StockAdjustment(models.Model):
    """Admin xato kirimni tuzatish yoki qo'shimcha kiritish"""
    batch = models.ForeignKey(StockBatch, on_delete=models.CASCADE, related_name='adjustments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    adjustment_type = models.CharField(max_length=20, choices=[
        ('increase', 'Miqdorni oshirish'),
        ('decrease', 'Miqdorni kamaytirish'),
        ('price_change', 'Narxni o‘zgartirish'),
        ('correction', 'To‘liq tuzatish'),
        ('return',       'Sotuv qaytarish'),      # ← yangi
    ])
    
    quantity_change = models.IntegerField(null=True, blank=True, help_text="Musbat - qo'shish, manfiy - ayirish")
    new_cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    reason = models.TextField(blank=True, verbose_name="Tuzatish sababi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adjustment #{self.id} - Batch {self.batch.id}"    
    

# ====================== SALE ======================
class Sale(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Faol'),
        (STATUS_CANCELLED, 'Bekor qilingan'),
    ]

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='sales')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cancelled_sales')

    objects = models.Manager()
    active_objects = NotCancelledManager()   # faqat active sotuvlar

    @property
    def item_count(self):
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    def full_cancel(self, cancelled_by=None, reason=""):
        if self.status == self.STATUS_CANCELLED:
            return

        from apps.services.sale_service import SaleService

        return SaleService.full_cancel_sale(
            sale=self,
            cancelled_by=cancelled_by,
            reason=reason
        )
    
    def cancel(self, cancelled_by=None):
        if self.status == self.STATUS_CANCELLED:
            return
        self.status = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by'])
    
    def __str__(self):
        return f"Sale #{self.id} - {self.client.name}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(StockBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='sale_items')
    quantity = models.PositiveIntegerField()
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price_at_sale = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    returned_quantity = models.PositiveIntegerField(default=0)

    def subtotal(self):
        return self.quantity * self.price_at_sale

    def profit(self):
        sold_qty = self.quantity - self.returned_quantity
        return sold_qty * (self.price_at_sale - self.cost_price_at_sale)
    
    def get_remaining_quantity(self):
        return self.quantity - self.returned_quantity
    
    class Meta:
        indexes = [models.Index(fields=['sale'])]

# ====================== SALERETURN (Qaytarish) ======================
class SaleReturn(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True, verbose_name="Qaytarish sababi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Qaytarish #{self.id} - Sale #{self.sale.id}"


class SaleReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE)
    returned_quantity = models.PositiveIntegerField()
    returned_to_batch = models.ForeignKey(StockBatch, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.returned_quantity} ta {self.sale_item.product.name}"
    

class Payment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)
    refunded_amount = models.DecimalField(
        max_digits=12, decimal_places=2, 
        default=Decimal('0')
    )
    
    is_cancelled = models.BooleanField(default=False)      # ← muhim farq
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cancelled_payments')

    objects = models.Manager()
    active_objects = NotCancelledManager()
    
    def get_remaining_amount(self):
        return self.amount - self.refunded_amount

    def is_fully_refunded(self):
        return self.refunded_amount >= self.amount
        
    def cancel(self, cancelled_by=None):
        if self.is_cancelled:
            return

        from django.db import transaction

        with transaction.atomic():
            client = Client.objects.select_for_update().get(pk=self.client.pk)

            amount = self.amount

            # ❗ reverse payment
            if client.advance_balance >= amount:
                client.advance_balance -= amount
            else:
                remaining = amount - client.advance_balance
                client.advance_balance = Decimal('0')
                client.total_debt += remaining

            client.save(update_fields=['total_debt', 'advance_balance'])

            self.is_cancelled = True
            self.cancelled_at = timezone.now()
            self.cancelled_by = cancelled_by
            self.save(update_fields=['is_cancelled', 'cancelled_at', 'cancelled_by'])

    def __str__(self):
        return f"{self.client.name} - {self.amount} so‘m"
    
class PaymentRefund(models.Model):
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name='refunds'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund {self.amount} — Payment #{self.payment.id}"
    
    
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        # Product
        ('product_create', 'Mahsulot qo\'shildi'),
        ('product_update', 'Mahsulot yangilandi'),
        ('product_delete', 'Mahsulot o\'chirildi'),
        # Stock / Batch
        ('stock_add',      'Stock kirim qilindi'),
        ('stock_adjust',   'Stock tuzatildi'),
        ('stock_delete',   'Batch o\'chirildi'),
        # Sale
        ('sale',           'Sotuv amalga oshirildi'),
        ('sale_return',    'Sotuv qaytarildi'),
        # Payment
        ('payment',        'To\'lov qabul qilindi'),
        ('payment_refund', 'To\'lov qaytarildi'),
        # Client
        ('client_create',  'Mijoz qo\'shildi'),
        ('client_update',  'Mijoz yangilandi'),
        ('client_delete',  'Mijoz o\'chirildi'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Foydalanuvchi")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Harakat turi")
    description = models.CharField(max_length=255, verbose_name="Qisqa tavsif")
    extra_data = models.JSONField(null=True, blank=True, verbose_name="To‘liq ma’lumot")  # modal uchun

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['-created_at'])]
        verbose_name = "Faoliyat tarixi"
        verbose_name_plural = "Faoliyat tarixi"

    def __str__(self):
        return f"{self.created_at} - {self.get_action_type_display()}"
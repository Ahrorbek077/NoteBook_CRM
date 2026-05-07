from django.db import models

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True) # Product, Client, StockBatch uchun
    
    def all_with_deleted(self):
        return super().get_queryset()
    

class NotCancelledManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_cancelled=False)
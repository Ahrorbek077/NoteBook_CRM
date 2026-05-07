from django.contrib import admin
from apps.products.models import Category, Product, Client, Region

admin.site.register(Category)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'is_active')
    list_filter = ('is_active', 'category')

    def get_queryset(self, request):
        return Product.all_objects.all()   # 🔥 hammasini ko‘rsatadi
    
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address', 'is_active')

    def get_queryset(self, request):
        return Client.all_objects.all()   # 🔥 hammasini ko‘rsatadi
    
# admin.py
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']    
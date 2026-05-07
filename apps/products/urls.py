from django.urls import path

from apps.products.views.web_views import (
    ProductCreateView,
    ProductListView,
    ProductDeleteView,
    ProductUpdateView,
    AddStockView,
    ProductBatchView,
    BatchAdjustmentsView,
    BatchDeleteView,
    CategorySaveView,
    CategoryDeleteView,
    ProductLauncherCreateView,
)

from apps.products.views.api_views import (
    ProductModalListView,
    FilteredProductsView,
    AddToCartView,
    GetCartView,
    ClearCartView,
    CreateSaleView,
    CreatePaymentView,
    SaleReturnView,
    SaleCancelView,
    StockAdjustmentView,
    PaymentRefundView,
)

app_name = 'products'

urlpatterns = [

    # ====================== WEB ======================
    path("", ProductListView.as_view(), name="product_list"),
    path("create/", ProductCreateView.as_view(), name="product_create"),
    path("update/", ProductUpdateView.as_view(), name="product_update"),
    path("delete/", ProductDeleteView.as_view(), name="product_delete"),
    path("launcher/create/", ProductLauncherCreateView.as_view(), name="product_launcher_create"),

    path('category/save/', CategorySaveView.as_view(), name='category-save'),
    path('category/delete/<int:pk>/', CategoryDeleteView.as_view(), name='category-delete'),

    # ====================== INVENTORY ======================
    path('stock/add/<int:product_id>/', AddStockView.as_view(), name='add-stock'),
    path('stock/adjust/<int:batch_id>/', StockAdjustmentView.as_view(), name='stock-adjustment'),
    path('batch/<int:batch_id>/adjustments/', BatchAdjustmentsView.as_view(), name='batch-adjustments'),
    path('batch/<int:batch_id>/delete/', BatchDeleteView.as_view(), name='batch-delete'),

    # ====================== PRODUCTS API ======================
    path('products/modal/', ProductModalListView.as_view(), name='products-modal'),
    path('products/filtered/', FilteredProductsView.as_view(), name='products-filtered'),
    path('product/<int:product_id>/batches/', ProductBatchView.as_view(), name='product-batches'),

    # ====================== CART ======================
    path('cart/add/<int:client_id>/', AddToCartView.as_view(), name='cart-add'),
    path('cart/<int:client_id>/', GetCartView.as_view(), name='cart-get'),
    path('cart/clear/<int:client_id>/', ClearCartView.as_view(), name='cart-clear'),

    # ====================== SALE ======================
    path('sale/create/<int:client_id>/', CreateSaleView.as_view(), name='sale-create'),
    path('sale/<int:sale_id>/return/', SaleReturnView.as_view(), name='sale-return'),
    path('sale/<int:sale_id>/cancel/', SaleCancelView.as_view(), name='sale-cancel'),

    # ====================== PAYMENT ======================
    path('payment/create/<int:client_id>/', CreatePaymentView.as_view(), name='payment-create'),
    path('payment/<int:payment_id>/refund/', PaymentRefundView.as_view(), name='payment-refund'),
]
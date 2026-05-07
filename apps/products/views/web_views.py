from apps.products.models import Product, StockBatch, Category, Region
from apps.products.forms import ProductForm, CategoryForm
from django.views.generic import ListView, CreateView, View, TemplateView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
import os
from apps.services.stock_service import StockService
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.accounts.mixins import AdminRequiredMixin


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "inventory.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        qs = Product.objects.select_related("category").order_by("-created_at")

        search = self.request.GET.get("search", "").strip()

        if search:

            qs = qs.filter(
                Q(name__icontains=search) |
                Q(slug__icontains=search)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProductForm()
        return context

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_ajax_response()

        return super().get(request, *args, **kwargs)

    def get_ajax_response(self):
        queryset = self.get_queryset()

        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get('page', 1)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        products_data = [
            {
                "id": p.id,
                "name": p.name,
                "price": str(p.price) if p.price else "0",
                "stock": p.stock,
                "image": p.image.url if p.image else None,
            }
            for p in page_obj
        ]

        return JsonResponse({
            "products": products_data,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "total_count": paginator.count,
        })


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy("products:product_list")

    def form_valid(self, form):
        product = form.save(commit=False)
        product.stock = 0
        product.save()
        return super().form_valid(form)
    
class ProductLauncherCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm

    def form_valid(self, form):
        product = form.save(commit=False)
        product.stock = 0
        product.save()
        return JsonResponse({
            "status":  "created",
            "id":      product.id,
            "name":    product.name,
            "price":   float(product.price),
        })

    def form_invalid(self, form):
        return JsonResponse({
            "status": "error",
            "errors": form.errors
        }, status=400)
    
class ProductDeleteView(LoginRequiredMixin, View):
    def post(self, request):
        product_id = request.POST.get("product_id")
        product = get_object_or_404(Product.all_objects, pk=product_id)

        if product.is_active:
            product.is_active = False
            product.save(update_fields=['is_active'])
            return JsonResponse({
                "status": "deleted", 
                "message": "Mahsulot o‘chirildi (soft delete)"
            })
        else:
            return JsonResponse({"status": "error", "message": "Mahsulot allaqachon o‘chirilgan"}, status=400)
    

class ProductUpdateView(View):
    def post(self, request):
        product_id = request.POST.get("product_id")
        try:
            product = get_object_or_404(Product, id=product_id)

            product.name = request.POST.get("name", product.name)

            price = request.POST.get("price")
            if price:
                product.price = Decimal(price)

            # Rasm yangilash
            if "image" in request.FILES:
                if product.image and os.path.isfile(product.image.path):
                    os.remove(product.image.path)
                product.image = request.FILES["image"]

            product.save()

            return JsonResponse({
                "status": "updated",
                "new_image_url": product.image.url if product.image else None,
                "new_name": product.name,
                "new_price": str(product.price)
            })

        except (ValueError, InvalidOperation):
            return JsonResponse({"status": "error", "message": "Narx noto'g'ri formatda"}, status=400)
        
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        

class AddStockView(View):
    """Har bir mahsulot qatoridagi Accordion orqali tez stok qo‘shish"""

    def post(self, request, product_id):
        try:
            product = get_object_or_404(Product.objects, id=product_id)

            quantity = int(request.POST.get('quantity', 0))
            cost_price = Decimal(request.POST.get('cost_price', '0'))

            if quantity <= 0 or cost_price <= 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Miqdor va tan narxi musbat bo‘lishi kerak!'
                }, status=400)

            StockService.add_stock(
                product=product,
                quantity=quantity,
                cost_price=cost_price
            )

            # 🔥 ENG MUHIM FIX
            product.refresh_from_db()

            return JsonResponse({
                'status': 'success',
                'message': f"{quantity} ta mahsulot {cost_price:,} so‘m narxda qo‘shildi!",
                'new_stock': product.stock,
                'product_id': product.id
            })

        except (ValueError, InvalidOperation):
            return JsonResponse({
                'status': 'error',
                'message': 'Miqdor yoki narx noto‘g‘ri'
            }, status=400)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)


class ProductBatchView(LoginRequiredMixin, TemplateView):
    template_name = "batch_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product_id = self.kwargs.get("product_id")
        product = get_object_or_404(Product, id=product_id)

        batches = StockBatch.objects.filter(product=product).order_by('-created_at')

        context.update({
            "product": product,
            "batches": batches
        })

        return context
    
class BatchAdjustmentsView(View):
    def get(self, request, batch_id):
        batch = get_object_or_404(StockBatch, id=batch_id)
        adjustments = batch.adjustments.select_related('user').order_by('-created_at')
        return JsonResponse({
            'status': 'success',
            'adjustments': [
                {
                    'adjustment_type': a.adjustment_type,
                    'quantity_change': a.quantity_change,
                    'new_cost_price': float(a.new_cost_price) if a.new_cost_price else None,
                    'reason': a.reason,
                    'created_at': a.created_at.strftime('%d.%m.%Y %H:%i'),
                }
                for a in adjustments
            ]
        })    
    
    
class BatchDeleteView(View):
    def post(self, request, batch_id):
        batch = get_object_or_404(StockBatch, id=batch_id)
        try:
            batch.soft_delete(user=request.user)
            return JsonResponse({'status': 'success'})
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        

class CategorySaveView(LoginRequiredMixin, View):
    def post(self, request):
        category_id = request.POST.get("id")

        if category_id:
            category = get_object_or_404(Category, pk=category_id)
        else:
            category = None

        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            obj = form.save()

            return JsonResponse({
                "status": "success",
                "id": obj.id,
                "name": obj.name,
            })

        return JsonResponse({
            "status": "error",
            "errors": form.errors
        }, status=400)
    

class CategoryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)

        if category.products.exists():
            return JsonResponse({
                "status": "error",
                "message": "Bu category ishlatilgan!"
            }, status=400)

        category.is_active = False  # soft delete
        category.save(update_fields=["is_active"])

        return JsonResponse({"status": "success"})
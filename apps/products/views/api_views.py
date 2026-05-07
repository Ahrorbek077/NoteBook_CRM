import json
import logging
from apps.products.models import Product, Client, Sale, StockBatch, Payment
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from apps.services.sale_service import SaleService
from apps.services.payment_service import PaymentService
from apps.services.stock_service import StockService
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views import View

logger = logging.getLogger(__name__)

# ====================== MAHSULOTLAR RO‘YXATI (Modal uchun) ======================
class ProductModalListView(View):
    def get(self, request):
        products = Product.objects.filter(stock__gt=0, is_active=True).order_by('name')
        data = list(products.values('id', 'name', 'price', 'stock'))
        return JsonResponse({'products': data})

# ====================== FILTERED PRODUCTS (Search + Category + Pagination) ======================
class FilteredProductsView(View):
    def get(self, request):
        query = request.GET.get('search', '').strip()
        category_id = request.GET.get('category')
        page_number = int(request.GET.get('page', 1))

        products = Product.objects.filter(stock__gt=0).select_related('category').order_by('name')

        if query:
            products = products.filter(name__icontains=query)
        if category_id:
            products = products.filter(category_id=category_id)

        paginator = Paginator(products, 10)
        page_obj = paginator.get_page(page_number)

        products_data = [
            {
                'id': p.id,
                'name': p.name,
                'price': str(p.price),
                'stock': p.stock,
            }
            for p in page_obj.object_list
        ]

        return JsonResponse({
            'products': products_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        })

# ====================== SAVATCHAGA QO‘SHISH ======================
class AddToCartView(View):
    def post(self, request, client_id):
        try:
            if not client_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Client ID required'
                }, status=400)

            data = json.loads(request.body or "{}")

            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))

            if not product_id:
                return JsonResponse({'status': 'error', 'message': 'Product ID required'}, status=400)

            if quantity <= 0:
                return JsonResponse({'status': 'error', 'message': 'Miqdor noto‘g‘ri'}, status=400)

            product = get_object_or_404(Product, id=product_id, is_active=True)

            cart_key = f'cart_client_{client_id}'
            cart = request.session.get(cart_key, [])

            # 🔥 tez ishlaydigan lookup
            cart_dict = {item['product_id']: item for item in cart}

            if product_id in cart_dict:
                new_qty = cart_dict[product_id]['quantity'] + quantity

                if product.stock < new_qty:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Yetarli stock mavjud emas'
                    }, status=400)

                cart_dict[product_id]['quantity'] = new_qty
            else:
                if product.stock < quantity:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Yetarli stock mavjud emas'
                    }, status=400)

                cart_dict[product_id] = {
                    'product_id': product.id,
                    'name': product.name,
                    'price': str(product.price),  # 🔥 float emas
                    'quantity': quantity
                }

            cart = list(cart_dict.values())

            request.session[cart_key] = cart
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'message': f"{product.name} savatchaga qo‘shildi",
                'cart_count': sum(item['quantity'] for item in cart)  # 🔥 to‘g‘ri count
            })

        except Exception as e:
            logger.error(f"AddToCart error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Server xatoligi'
            }, status=500)
                
# ====================== SAVATCHA MA’LUMOTLARI ======================
class GetCartView(View):
    def get(self, request, client_id):
        try:
            if not client_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Client ID required'
                }, status=400)

            cart_key = f'cart_client_{client_id}'
            cart = request.session.get(cart_key, [])

            total = sum(Decimal(item['price']) * item['quantity'] for item in cart)

            return JsonResponse({
                'status': 'success',
                'cart': cart,
                'total': float(total),
                'item_count': sum(item['quantity'] for item in cart)
            })

        except Exception as e:
            logger.error(f"GetCart error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Server xatoligi'
            }, status=500)
        
# ====================== SAVATCHANI TOZALASH ======================
class ClearCartView(View):
    def post(self, request, client_id):
        try:
            if not client_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Client ID required'
                }, status=400)

            cart_key = f'cart_client_{client_id}'
            request.session[cart_key] = []
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'message': 'Savatcha tozalandi'
            })

        except Exception as e:
            logger.error(f"ClearCart error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Server xatoligi'
            }, status=500)
        
# ====================== SOTISH (Create Sale) ======================
class CreateSaleView(View):
    def post(self, request, client_id):
        try:
            if not client_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Client ID required'
                }, status=400)

            client = get_object_or_404(Client, id=client_id)

            cart_key = f'cart_client_{client_id}'
            cart = request.session.get(cart_key, [])

            if not cart:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Savatcha bo‘sh'
                }, status=400)

            sale = SaleService.create_sale_from_cart(
                client=client,
                cart_items=[
                    {
                        'product_id': item['product_id'],
                        'quantity': item['quantity']
                    } for item in cart
                ],
                user=request.user
            )

            # 🔥 savatchani tozalash
            request.session[cart_key] = []
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'message': 'Sotuv muvaffaqiyatli yaratildi',
                'sale_id': sale.id,
                'total_amount': float(sale.total_amount)
            })

        except Exception as e:
            logger.error(f"CreateSale error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)  # bu yerda ko‘rsatish mumkin (business error)
            }, status=400)
        
# ====================== TO‘LOV QABUL QILISH ======================
class CreatePaymentView(View):
    def post(self, request, client_id):
        try:
            client = get_object_or_404(Client, id=client_id)
            data = json.loads(request.body)
            amount = Decimal(data.get('amount', '0'))
            note = data.get('note', '')

            PaymentService.create_payment(
                client=client,
                amount=amount,
                user=request.user,
                note=note
            )

            client.refresh_from_db()

            return JsonResponse({
                'status': 'success',
                'message': f"{amount} so‘m to‘lov qabul qilindi",
                'total_debt': float(client.total_debt),
                'advance_balance': float(client.advance_balance)
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

class PaymentRefundView(LoginRequiredMixin, View):
    def post(self, request, payment_id):
        try:
            payment = get_object_or_404(
                Payment.objects.select_related('client'), 
                id=payment_id
            )

            if payment.is_cancelled:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bekor qilingan to\'lovni qaytarib bo\'lmaydi'
                }, status=400)

            if payment.get_remaining_amount() <= 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bu to\'lov allaqachon to\'liq qaytarilgan'
                }, status=400)

            data = json.loads(request.body)
            amount = Decimal(str(data.get('amount', 0)))
            reason = data.get('reason', '').strip()

            PaymentService.refund_payment(
                payment=payment,
                amount=amount,
                user=request.user,
                reason=reason
            )

            return JsonResponse({
                'status': 'success',
                'message': f"{amount:,.0f} so'm muvaffaqiyatli qaytarildi",
                'remaining': float(payment.get_remaining_amount()),
            })

        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ====================== STOCKBATCH TUZATISH ======================
ALLOWED_TYPES = {'increase', 'decrease', 'price_change', 'correction'}

class StockAdjustmentView(View):
    def post(self, request, batch_id):
        try:
            batch = get_object_or_404(StockBatch, id=batch_id)

            # Sarflangan batchni tekshirish
            if batch.remaining_quantity != batch.quantity_received:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bu batch allaqachon ishlatilgan, o\'zgartirib bo\'lmaydi'
                }, status=400)

            quantity_change = int(request.POST.get('quantity_change', 0))
            new_cost_price  = request.POST.get('new_cost_price', '').strip()
            reason          = request.POST.get('reason', '').strip()

            if not reason:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Sabab kiritish majburiy'
                }, status=400)

            new_cost_price = Decimal(new_cost_price) if new_cost_price else None

            if quantity_change == 0 and not new_cost_price:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Miqdor yoki narx o\'zgarishi kiritilmadi'
                }, status=400)

            adjustment = StockService.adjust_stock(
                batch=batch,
                quantity_change=quantity_change,
                new_cost_price=new_cost_price,
                user=request.user,
                reason=reason
            )

            # Fresh from DB
            batch.refresh_from_db()
            batch.product.refresh_from_db()

            return JsonResponse({
                'status': 'success',
                'message': 'Muvaffaqiyatli tuzatildi',
                'adjustment_id':  adjustment.id,
                'new_remaining':  batch.remaining_quantity,
                'new_received':   batch.quantity_received,
                'new_cost_price': float(batch.cost_price),
                'new_stock':      batch.product.stock,
            })

        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ====================== Butun Sotuvni Bekor qilish (Cancel) ======================
class SaleCancelView(View):
    """Butun sotuvni bekor qilish (Cancel)"""
    
    def post(self, request, sale_id):
        try:
            sale = get_object_or_404(Sale.all_objects, id=sale_id)

            if sale.status == Sale.STATUS_CANCELLED:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Sotuv allaqachon bekor qilingan'
                }, status=400)

            sale.full_cancel(cancelled_by=request.user)

            return JsonResponse({
                'status': 'success',
                'message': 'Sotuv bekor qilindi',
                'sale_id': sale.id
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        
# ====================== SOTUVNI BEKOR QILISH ======================        
class SaleReturnView(View):
    def post(self, request, sale_id):
        try:
            sale = get_object_or_404(Sale, id=sale_id)

            print("=== RETURN REQUEST DEBUG ===")
            print("Raw body:", request.body.decode('utf-8') if request.body else "EMPTY BODY")
            
            if sale.status == Sale.STATUS_CANCELLED:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bekor qilingan sotuvni qaytarib bo‘lmaydi'
                }, status=400)

            try:
                data = json.loads(request.body)
                print("Parsed data:", data)
            except json.JSONDecodeError as e:
                print("JSON Decode Error:", str(e))
                return JsonResponse({'status': 'error', 'message': f'JSON format xato: {str(e)}'}, status=400)
            
            print("full_return flag:", data.get('full_return'))
            print("items from frontend:", data.get('items'))

            if data.get('full_return'):
                remaining_items = [
                    {'sale_item_id': item.id, 'quantity': item.get_remaining_quantity()}
                    for item in sale.items.all()
                    if item.get_remaining_quantity() > 0
                ]
                print("Calculated remaining_items:", remaining_items)
                
                if not remaining_items:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Qaytariladigan mahsulot qolmagan'
                    }, status=400)

                return_data = remaining_items
            else:
                return_data = data.get('items', [])

            print("Final return_data sent to process_return:", return_data)

            sale_return = SaleService.process_return(
                sale=sale,
                return_data=return_data,
                user=request.user,
                reason=data.get('reason', '').strip()
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Mahsulot(lar) muvaffaqiyatli qaytarildi',
                'return_id': sale_return.id,
                'sale_id': sale.id
            })

        except Exception as e:
            import traceback
            print("FULL EXCEPTION:")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
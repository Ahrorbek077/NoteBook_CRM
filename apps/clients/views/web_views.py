from apps.products.models import Product, Client, Category, Sale, SaleItem, SaleReturn, SaleReturnItem, PaymentRefund, Region
from apps.clients.forms import ClientForm, RegionForm
from django.views.generic import ListView, CreateView, View, DetailView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Prefetch, F, ExpressionWrapper, DecimalField
from django.contrib.auth.mixins import LoginRequiredMixin
from decimal import Decimal
from django.db.models.functions import Coalesce


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "client.html"
    context_object_name = "clients"
    paginate_by = 12

    def get_queryset(self):
        qs = Client.objects.select_related('region').order_by("-created_at")
        search = self.request.GET.get("search", "").strip()
        region_id = self.request.GET.get("region", "").strip()

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search)
            )
        if region_id:
            qs = qs.filter(region_id=region_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ClientForm()
        context['regions'] = Region.objects.filter(is_active=True)
        context['selected_region'] = self.request.GET.get("region", "")
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
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        clients_data = [
            {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "address": c.address or "",
                "region_id": c.region_id or "",
                "region_name": c.region.name if c.region else "",
                "total_debt": float(c.total_debt),
                "advance_balance": float(c.advance_balance),
            }
            for c in page_obj
        ]

        return JsonResponse({
            "clients": clients_data,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "total_count": paginator.count,
        })


# ====================== CREATE ======================
class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm

    def form_valid(self, form):
        form.save()
        return JsonResponse({"status": "created"})

    def form_invalid(self, form):
        return JsonResponse({
            "status": "error",
            "message": "Formada xatolik bor",
            "errors": form.errors
        }, status=400)


# ====================== UPDATE ======================
class ClientUpdateView(View):
    def post(self, request):
        client_id = request.POST.get("client_id")
        try:
            client = Client.all_objects.get(id=client_id)
        except Client.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Client topilmadi"}, status=404)

        client.name    = request.POST.get("name", client.name).strip()
        client.phone   = request.POST.get("phone", client.phone).strip()
        client.address = request.POST.get("address", client.address).strip()

        region_id = request.POST.get("region_id")
        if region_id:
            client.region_id = int(region_id)
        elif region_id == "":
            client.region = None

        client.save()
        return JsonResponse({
            "status": "updated",
            "region_name": client.region.name if client.region else "",
        })

    

# ====================== DELETE ======================
class ClientDeleteView(View):
    def post(self, request):
        client_id = request.POST.get("client_id")
        client = get_object_or_404(Client.all_objects, pk=client_id)   # all_objects bilan qidiramiz

        if client.is_active:
            client.is_active = False
            client.save(update_fields=['is_active'])
            return JsonResponse({"status": "deleted", "message": "Mijoz soft delete qilindi"})
        else:
            return JsonResponse({"status": "error", "message": "Mijoz allaqachon o‘chirilgan"}, status=400)


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "client_detail.html"
    context_object_name = "client"

    # 🔥 client + region birga olib kelamiz
    def get_queryset(self):
        return Client.objects.select_related('region')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object

        # ==================== SALES ====================
        sales = client.sales.filter(
            status=Sale.STATUS_ACTIVE
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=SaleItem.objects.select_related('product')
            )
        ).order_by('-created_at')[:30]

        # ==================== SALE RETURNS ====================
        sale_returns = SaleReturn.objects.filter(
            sale__client=client
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=SaleReturnItem.objects.select_related(
                    'sale_item__product'
                )
            )
        ).select_related('sale').order_by('-created_at')[:30]

        # ==================== PAYMENTS (FIXED) ====================
        payments_qs = client.payments.filter(is_cancelled=False)

        payments = list(
            payments_qs.order_by('-created_at')[:30]
        )

        # ==================== PAYMENT REFUNDS ====================
        payment_refunds = PaymentRefund.objects.filter(
            payment__client=client
        ).select_related('payment').order_by('-created_at')[:30]

        # ==================== TOTAL SOLD ====================
        total_sold = SaleItem.objects.filter(
            sale__client=client,
            sale__status=Sale.STATUS_ACTIVE
        ).aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        (F('quantity') - F('returned_quantity')) * F('price_at_sale'),
                        output_field=DecimalField()
                    )
                ),
                Decimal('0')
            )
        )['total']

        # ==================== TOTAL PAID (NO DUPLICATE QUERY) ====================
        total_paid = payments_qs.aggregate(
            total=Coalesce(
                Sum(
                    F('amount') - F('refunded_amount'),
                    output_field=DecimalField()
                ),
                Decimal('0')
            )
        )['total']

        # ==================== HISTORY ====================
        history = []

        # -------- SALES --------
        for sale in sales:
            items_list = sale.items.all()

            serialized_items = []
            item_count = 0

            for item in items_list:
                item_count += item.quantity

                serialized_items.append({
                    'id': item.id,
                    'product': {'name': item.product.name},
                    'quantity': item.quantity,
                    'returned_quantity': item.returned_quantity,
                    'remaining': item.get_remaining_quantity(),
                    'price_at_sale': float(item.price_at_sale),
                    'subtotal': float(item.price_at_sale * item.quantity),
                    'returned_subtotal': float(item.price_at_sale * item.returned_quantity),
                })

            history.append({
                'date': sale.created_at,
                'type': 'sale',
                'display_type': 'Sotuv',
                'badge': 'Qarz',
                'badge_color': 'bg-danger',
                'amount': float(sale.total_amount),
                'is_positive': False,
                'details': f"{item_count} ta mahsulot",
                'items': serialized_items,
                'serialized_items': serialized_items,
                'sale_id': sale.id,
            })

        # -------- SALE RETURNS --------
        for sale_return in sale_returns:
            returned_items = sale_return.items.all()

            total_returned = 0
            serialized_return_items = []

            for i in returned_items:
                subtotal = i.returned_quantity * i.sale_item.price_at_sale
                total_returned += subtotal

                serialized_return_items.append({
                    'product_name': i.sale_item.product.name,
                    'quantity': i.returned_quantity,
                    'price': float(i.sale_item.price_at_sale),
                    'subtotal': float(subtotal),
                })

            history.append({
                'date': sale_return.created_at,
                'type': 'sale_return',
                'display_type': 'Qaytarish',
                'badge': 'Qaytarildi',
                'badge_color': 'bg-warning text-dark',
                'amount': float(total_returned),
                'is_positive': True,
                'details': sale_return.reason or f"Sotuv #{sale_return.sale.id} dan",
                'items': serialized_return_items,
                'return_id': sale_return.id,
                'sale_id': sale_return.sale.id,
            })

        # -------- PAYMENTS --------
        for payment in payments:
            history.append({
                'date': payment.created_at,
                'type': 'payment',
                'display_type': "To'lov",
                'badge': "To'langan",
                'badge_color': 'bg-success',
                'amount': float(payment.amount),
                'is_positive': True,
                'details': payment.note or 'Izohsiz',
                'payment_id': payment.id,
                'note': payment.note or '',
                'refunded_amount': float(payment.refunded_amount),
                'remaining_amount': float(payment.get_remaining_amount()),
                'is_fully_refunded': payment.is_fully_refunded(),
            })

        # -------- PAYMENT REFUNDS --------
        for refund in payment_refunds:
            history.append({
                'date': refund.created_at,
                'type': 'payment_refund',
                'display_type': "To'lov qaytarildi",
                'badge': 'Refund',
                'badge_color': 'bg-warning text-dark',
                'amount': float(refund.amount),
                'is_positive': False,
                'details': refund.reason or f"To'lov #{refund.payment.id} dan",
                'refund_id': refund.id,
                'payment_id': refund.payment.id,
                'reason': refund.reason or '',
            })

        # 🔥 SORT
        history.sort(key=lambda x: x['date'], reverse=True)

        # 🔥 PAGINATION
        paginator = Paginator(history, 15)
        page_number = self.request.GET.get('history_page', 1)
        page_obj = paginator.get_page(page_number)

        # ==================== CONTEXT ====================
        context.update({
            'history': page_obj.object_list,
            'history_page_obj': page_obj,
            'sales': sales,
            'payments': payments,
            'total_sold': total_sold,
            'total_paid': total_paid,
            'calculated_debt': client.total_debt,
            'products': Product.objects.filter(stock__gt=0)
                .only('id', 'name', 'stock')
                .order_by('name'),
            'categories': Category.objects.filter(is_active=True)
                .only('id', 'name')
                .order_by('name'),
        })

        return context
    

class RegionSaveView(View):
    def post(self, request):
        region_id = request.POST.get("id")

        if region_id:
            region = get_object_or_404(Region, pk=region_id)
        else:
            region = None

        form = RegionForm(request.POST, instance=region)

        if form.is_valid():
            obj = form.save()

            return JsonResponse({
                "status": "success",
                "id": obj.id,
                "name": obj.name,
                "order": obj.order
            })

        return JsonResponse({
            "status": "error",
            "errors": form.errors
        }, status=400)


class RegionDeleteView(View):
    def post(self, request, pk):
        region = get_object_or_404(Region, pk=pk)

        if region.clients.exists():  # 🔥 check
            return JsonResponse({
                "status": "error",
                "message": "Bu region ishlatilgan!"
            }, status=400)

        region.is_active = False
        region.save(update_fields=["is_active"])

        return JsonResponse({"status": "success"})
    
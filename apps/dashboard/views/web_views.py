from django.contrib.auth.mixins import LoginRequiredMixin
from apps.products.models import ActivityLog, Region, Category
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from apps.accounts.mixins import AdminRequiredMixin

class LauncherView(LoginRequiredMixin, TemplateView):
    template_name = "launcher.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["regions"] = Region.objects.all()
        context["categories"] = Category.objects.all().order_by("name")

        return context
    
class DashboardView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"


class ActivityLogView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = ActivityLog
    template_name = "history.html"
    context_object_name = "logs"
    paginate_by = 30

    ACTION_CLASS_MAP = {
        'sale':           ('badge-sale',    'fa-shopping-cart'),
        'sale_return':    ('badge-return',  'fa-undo'),
        'payment':        ('badge-payment', 'fa-credit-card'),
        'payment_refund': ('badge-refund',  'fa-undo'),
        'product_create': ('badge-create',  'fa-plus'),
        'product_update': ('badge-update',  'fa-edit'),
        'product_delete': ('badge-delete',  'fa-trash'),
        'stock_add':      ('badge-stock',   'fa-boxes'),
        'stock_adjust':   ('badge-adjust',  'fa-sliders-h'),
        'stock_delete':   ('badge-delete',  'fa-trash'),
        'client_create':  ('badge-create',  'fa-user-plus'),
        'client_update':  ('badge-update',  'fa-user-edit'),
        'client_delete':  ('badge-delete',  'fa-user-times'),
    }

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('user').order_by('-created_at')

        search      = self.request.GET.get('search', '').strip()
        action_type = self.request.GET.get('action_type', '').strip()
        date_from   = self.request.GET.get('date_from', '').strip()
        date_to     = self.request.GET.get('date_to', '').strip()

        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(user__username__icontains=search)
            )
        if action_type:
            qs = qs.filter(action_type=action_type)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_choices'] = ActivityLog.ACTION_CHOICES
        context['selected_type']  = self.request.GET.get('action_type', '')
        return context

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_ajax_response()
        return super().get(request, *args, **kwargs)

    def get_ajax_response(self):
        queryset   = self.get_queryset()
        paginator  = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except Exception:
            page_obj = paginator.page(1)

        logs_data = []
        for log in page_obj:
            cls, icon = self.ACTION_CLASS_MAP.get(
                log.action_type, ('badge-secondary', 'fa-circle')
            )
            logs_data.append({
                'id':           log.id,
                'created_at':   log.created_at.strftime('%d.%m.%Y %H:%M'),
                'user':         log.user.username if log.user else 'Tizim',
                'action_type':  log.action_type,
                'action_label': log.get_action_type_display(),
                'action_class': cls,
                'action_icon':  icon,
                'description':  log.description,
                'extra_data':   log.extra_data or {},
            })

        global_qs = ActivityLog.objects.all()
        counts_qs = global_qs.values("action_type").annotate(c=Count("id"))
        counts = {row["action_type"]: row["c"] for row in counts_qs}

        return JsonResponse({
            'logs':        logs_data,
            'page':        page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next':    page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
            "counts": counts,
        })
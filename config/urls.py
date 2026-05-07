# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return redirect('accounts:login')

urlpatterns = [
    path('', root_redirect),
    path('admin/', admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path('clients/', include('apps.clients.urls')),
    path('products/', include('apps.products.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
]

handler403 = 'apps.accounts.views.error_403'
handler404 = 'apps.accounts.views.error_404'
handler500 = 'apps.accounts.views.error_500'

# Media fayllar — production da ham ishlashi uchun
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# if settings.DEBUG:
#     import debug_toolbar

#     urlpatterns += [
#         path('__debug__/', include(debug_toolbar.urls)),
#     ] #DEBUG TOOLBAR
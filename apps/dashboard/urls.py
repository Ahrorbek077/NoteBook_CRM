from django.urls import path
from apps.dashboard.views.web_views import DashboardView, LauncherView, ActivityLogView
from apps.dashboard.views.api_views import dashboard_api

app_name = 'dashboard'

urlpatterns = [
    path('', LauncherView.as_view(), name='launcher'),
    path('template/', DashboardView.as_view(), name='dashboard'),
    path('history/', ActivityLogView.as_view(), name='activity-log'),
    path('api/dashboard/', dashboard_api, name='dashboard_api'),
]
from django.urls import path
from apps.clients.views.web_views import ClientListView, ClientCreateView, ClientDeleteView, ClientUpdateView, ClientDetailView, RegionSaveView, RegionDeleteView

app_name = 'clients'

urlpatterns = [
    path('list/', ClientListView.as_view(), name='client_list'),
    path('create/', ClientCreateView.as_view(), name='client_create'),
    path('delete/', ClientDeleteView.as_view(), name='client_delete'),
    path('update/', ClientUpdateView.as_view(), name='client_update'),
    path('client/<int:pk>/', ClientDetailView.as_view(), name='client_detail'),
    
    path('region/save/', RegionSaveView.as_view(), name='region-save'),
    path('region/delete/<int:pk>/', RegionDeleteView.as_view(), name='region-delete'),

]
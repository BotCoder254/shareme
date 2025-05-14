from django.urls import path
from . import views

# app_name = 'tenants'

urlpatterns = [
    path('signup/', views.tenant_signup, name='tenant_signup'),
    path('success/', views.tenant_success, name='tenant_success'),
    path('list/', views.tenant_list, name='tenant_list'),
    path('detail/<uuid:tenant_id>/', views.tenant_detail, name='tenant_detail'),
] 
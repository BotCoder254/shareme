from django.urls import path, include
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stats/', views.stats, name='stats'),
    path('about/', views.about, name='about'),
    path('features/', views.features, name='features'),
    path('contact/', views.contact, name='contact'),
    path('tenants/', include('tenants.urls')),
] 
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/', views.notification_detail, name='detail'),
    path('<int:notification_id>/read/', views.mark_as_read, name='mark_as_read'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),
    path('unread-count/', views.get_unread_count, name='unread_count'),
] 
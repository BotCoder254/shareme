from django.contrib import admin
from .models import Notification

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'read', 'created_at')
    list_filter = ('notification_type', 'read', 'created_at')
    search_fields = ('recipient__username', 'title', 'message')
    date_hierarchy = 'created_at'
    
admin.site.register(Notification, NotificationAdmin)

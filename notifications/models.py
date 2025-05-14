from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

class Notification(models.Model):
    """Model to store user notifications"""
    
    NOTIFICATION_TYPES = (
        ('file_upload', 'File Uploaded'),
        ('file_share', 'File Shared'),
        ('storage_warning', 'Storage Warning'),
        ('folder_create', 'Folder Created'),
        ('system', 'System Notification'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # For linking to specific objects (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # URL to redirect to when notification is clicked
    link = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type}: {self.title} (to {self.recipient.username})"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read = True
        self.save()
        
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, sender=None, link=None, content_object=None):
        """Create a new notification"""
        notification = cls(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            sender=sender,
            link=link
        )
        
        if content_object:
            notification.content_object = content_object
            
        notification.save()
        return notification

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from files.models import FileItem, Folder, SharedFile, SharedFolder
from accounts.models import UserProfile
from django.urls import reverse
from django.utils import timezone

from .models import Notification

# File upload notification
@receiver(post_save, sender=FileItem)
def file_upload_notification(sender, instance, created, **kwargs):
    if created:
        # Create notification for file upload
        Notification.create_notification(
            recipient=instance.user,
            notification_type='file_upload',
            title='File Uploaded Successfully',
            message=f'Your file "{instance.title}" has been uploaded successfully.',
            link=reverse('files:file_detail', args=[instance.id]),
            content_object=instance
        )

# Storage warning notification (when storage usage goes above 90%)
@receiver(post_save, sender=UserProfile)
def storage_warning_notification(sender, instance, **kwargs):
    user = instance.user
    storage_usage_percentage = instance.get_storage_usage_percentage()
    
    # Check if storage usage is above 90%
    if storage_usage_percentage > 90:
        # Check if there's already a recent storage warning notification
        recent_notification = Notification.objects.filter(
            recipient=user,
            notification_type='storage_warning',
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).exists()
        
        if not recent_notification:
            Notification.create_notification(
                recipient=user,
                notification_type='storage_warning',
                title='Storage Space Almost Full',
                message=f'Your storage is {storage_usage_percentage}% full. Consider deleting old files or upgrading your storage plan.',
                link=reverse('accounts:profile')
            )

# File sharing notification
@receiver(post_save, sender=SharedFile)
def file_sharing_notification(sender, instance, created, **kwargs):
    if created:
        # Notify the person with whom the file is shared
        Notification.create_notification(
            recipient=instance.shared_with,
            notification_type='file_share',
            title='File Shared With You',
            message=f'{instance.shared_by.username} has shared the file "{instance.file.title}" with you.',
            sender=instance.shared_by,
            link=reverse('files:file_detail', args=[instance.file.id]),
            content_object=instance.file
        )

# Folder creation notification
@receiver(post_save, sender=Folder)
def folder_creation_notification(sender, instance, created, **kwargs):
    if created:
        # Create notification for folder creation
        Notification.create_notification(
            recipient=instance.user,
            notification_type='folder_create',
            title='Folder Created',
            message=f'Your folder "{instance.name}" has been created successfully.',
            link=reverse('files:folder_contents', args=[instance.id]),
            content_object=instance
        )

# Folder sharing notification
@receiver(post_save, sender=SharedFolder)
def folder_sharing_notification(sender, instance, created, **kwargs):
    if created:
        # Notify the person with whom the folder is shared
        Notification.create_notification(
            recipient=instance.shared_with,
            notification_type='file_share',
            title='Folder Shared With You',
            message=f'{instance.shared_by.username} has shared the folder "{instance.folder.name}" with you.',
            sender=instance.shared_by,
            link=reverse('files:folder_contents', args=[instance.folder.id]),
            content_object=instance.folder
        ) 
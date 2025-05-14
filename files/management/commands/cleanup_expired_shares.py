from django.core.management.base import BaseCommand
from django.utils import timezone
from files.models import SharedFile, SharedFolder
from notifications.models import Notification

class Command(BaseCommand):
    help = 'Clean up expired file and folder shares'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        self.stdout.write(f"Starting cleanup of expired shares at {now}")
        
        # Find expired file shares
        expired_file_shares = SharedFile.objects.filter(
            expires_at__lt=now,
            expires_at__isnull=False
        )
        
        count_file = 0
        for share in expired_file_shares:
            # Create a notification for the user whose share has expired
            try:
                Notification.create_notification(
                    recipient=share.shared_with,
                    notification_type='system',
                    title='File Share Expired',
                    message=f'Your access to "{share.file.title}" has expired. The share was removed.',
                    sender=share.shared_by
                )
                
                # Also notify the file owner that the share has expired
                Notification.create_notification(
                    recipient=share.shared_by,
                    notification_type='system',
                    title='File Share Expired',
                    message=f'Your share of "{share.file.title}" with {share.shared_with.username} has expired and was removed.',
                )
                
                self.stdout.write(f"Removing expired file share: {share}")
                share.delete()
                count_file += 1
            except Exception as e:
                self.stderr.write(f"Error processing file share {share.id}: {str(e)}")
        
        # Find expired folder shares
        expired_folder_shares = SharedFolder.objects.filter(
            expires_at__lt=now,
            expires_at__isnull=False
        )
        
        count_folder = 0
        for share in expired_folder_shares:
            # Create a notification for the user whose share has expired
            try:
                Notification.create_notification(
                    recipient=share.shared_with,
                    notification_type='system',
                    title='Folder Share Expired',
                    message=f'Your access to folder "{share.folder.name}" has expired. The share was removed.',
                    sender=share.shared_by
                )
                
                # Also notify the folder owner that the share has expired
                Notification.create_notification(
                    recipient=share.shared_by,
                    notification_type='system',
                    title='Folder Share Expired',
                    message=f'Your share of folder "{share.folder.name}" with {share.shared_with.username} has expired and was removed.',
                )
                
                self.stdout.write(f"Removing expired folder share: {share}")
                share.delete()
                count_folder += 1
            except Exception as e:
                self.stderr.write(f"Error processing folder share {share.id}: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully removed {count_file} expired file shares and {count_folder} expired folder shares.')
        ) 
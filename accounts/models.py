from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
import uuid

def get_profile_image_path(instance, filename):
    """Generate a unique file path for the profile image"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('profile_images', filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=get_profile_image_path, default='profile_images/default.png')
    bio = models.TextField(max_length=500, blank=True)
    storage_used = models.BigIntegerField(default=0)  # Used storage in bytes
    storage_limit = models.BigIntegerField(default=1073741824)  # Default 1GB limit (in bytes)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_storage_usage_percentage(self):
        """Return the percentage of storage used"""
        if self.storage_limit == 0:
            return 0
        return min(100, int((self.storage_used / self.storage_limit) * 100))
    
    def get_readable_storage_used(self):
        """Convert storage_used to readable format (KB, MB, GB)"""
        size = self.storage_used
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024
    
    def get_readable_storage_limit(self):
        """Convert storage_limit to readable format (KB, MB, GB)"""
        size = self.storage_limit
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024
            
    def get_available_storage_readable(self):
        """Get available storage in readable format"""
        available = max(0, self.storage_limit - self.storage_used)
        size = available
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new User"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    instance.profile.save()

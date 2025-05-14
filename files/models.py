from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
import uuid
from django.contrib.auth.hashers import check_password

def get_file_path(instance, filename):
    """Generate a unique file path for the uploaded file"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

class FileCategory(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='file')
    color = models.CharField(max_length=20, default='#3B82F6')  # Default blue color
    
    class Meta:
        verbose_name_plural = "File Categories"
    
    def __str__(self):
        return self.name

class Folder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'name', 'parent')
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent}/{self.name}"
        return self.name
    
    def get_path(self):
        """Return the full path of the folder"""
        if not self.parent:
            return self.name
        return f"{self.parent.get_path()}/{self.name}"
    
    def get_all_files(self):
        """Return all files in this folder and its subfolders"""
        files = list(self.files.all())
        for subfolder in self.subfolders.all():
            files.extend(subfolder.get_all_files())
        return files

class FileItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=get_file_path)
    file_size = models.BigIntegerField(default=0)  # Size in bytes
    category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    is_favorite = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title
    
    def extension(self):
        return os.path.splitext(self.file.name)[1][1:].upper()
    
    def filename(self):
        return os.path.basename(self.file.name)
    
    def get_readable_file_size(self):
        """Convert file size to readable format (KB, MB, GB)"""
        return self.get_readable_size(self.file_size)
    
    @staticmethod
    def get_readable_size(size_in_bytes):
        """Static method to convert any size in bytes to readable format"""
        size = size_in_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024
    
    def get_folder_path(self):
        """Return the folder path of the file"""
        if not self.folder:
            return "Root"
        return self.folder.get_path()
            
class SharedFile(models.Model):
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='shared_with')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_files')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_files')
    access_level = models.CharField(max_length=10, choices=[
        ('view', 'View'),
        ('edit', 'Edit'),
    ], default='view')
    shared_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('file', 'shared_with')
        
    def __str__(self):
        return f"{self.file.title} shared with {self.shared_with.username}"

class SharedFolder(models.Model):
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='shared_with')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_folders')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_folders')
    access_level = models.CharField(max_length=10, choices=[
        ('view', 'View'),
        ('edit', 'Edit'),
    ], default='view')
    shared_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('folder', 'shared_with')
        
    def __str__(self):
        return f"{self.folder.name} shared with {self.shared_with.username}"

class FileShareLink(models.Model):
    """Model for public sharing links with advanced options"""
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='share_links', null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='share_links', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_share_links')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    access_count = models.IntegerField(default=0)
    max_access_count = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        item_name = self.file.title if self.file else self.folder.name
        return f"Share link for {item_name}"
    
    def get_absolute_url(self):
        """Get the public URL for this share link"""
        return f"/share/{self.uuid}"
    
    def is_valid(self):
        """Check if the link is still valid based on expiration date and access count"""
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_access_count and self.access_count >= self.max_access_count:
            return False
        return True
    
    def check_password(self, raw_password):
        """Check if the provided password matches"""
        if not self.password:
            return True
        return check_password(raw_password, self.password)
    
    def increment_access_count(self):
        """Increment the access count and save"""
        self.access_count += 1
        self.save()

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
import uuid
from django.contrib.auth.hashers import check_password
import math
from pathlib import Path
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

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
    deleted_at = models.DateTimeField(null=True, blank=True)
    
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

    def get_absolute_url(self):
        return f"/files/folders/{self.id}/"
    
    def get_all_subfolders(self):
        """Get all subfolders recursively"""
        subfolders = list(self.subfolders.all())
        for subfolder in list(subfolders):
            subfolders.extend(subfolder.get_all_subfolders())
        return subfolders
    
    def is_in_trash(self):
        """Check if the folder is in trash"""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """Move the folder to trash"""
        self.deleted_at = timezone.now()
        self.save()
        
        # Also move all files in the folder to trash
        for file in self.files.all():
            file.soft_delete()
        
        # And all subfolders
        for subfolder in self.subfolders.all():
            subfolder.soft_delete()
            
    def restore(self):
        """Restore the folder from trash"""
        self.deleted_at = None
        self.save()
        
        # Also restore all files in the folder
        for file in self.files.filter(deleted_at__isnull=False):
            file.restore()
        
        # And all subfolders
        for subfolder in self.subfolders.filter(deleted_at__isnull=False):
            subfolder.restore()

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
    deleted_at = models.DateTimeField(null=True, blank=True)  # For soft delete/trash functionality
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    
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
        return FileItem.get_readable_size(self.file_size)
    
    @classmethod
    def get_readable_size(cls, size_in_bytes):
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
    
    def soft_delete(self):
        """Soft delete file (move to trash)"""
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """Restore file from trash"""
        self.deleted_at = None
        self.save()
    
    def is_in_trash(self):
        """Check if file is in trash"""
        return self.deleted_at is not None
    
    def get_current_version(self):
        """Get the current version of this file"""
        try:
            return self.versions.get(is_current=True)
        except FileVersion.DoesNotExist:
            return None
    
    def get_version_count(self):
        """Get the total number of versions for this file"""
        return self.versions.count()

    def get_absolute_url(self):
        return f"/files/{self.id}/"
    
    def readable_size(self):
        """Human-readable file size"""
        return FileItem.get_readable_size(self.file_size)
    
    def is_image(self):
        """Check if the file is an image"""
        img_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
        return self.extension().lower() in img_extensions
    
    def is_document(self):
        """Check if the file is a document"""
        doc_extensions = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx']
        return self.extension().lower() in doc_extensions
    
    def is_video(self):
        """Check if the file is a video"""
        video_extensions = ['mp4', 'avi', 'mov', 'wmv', 'mkv', 'webm']
        return self.extension().lower() in video_extensions
    
    def is_audio(self):
        """Check if the file is audio"""
        audio_extensions = ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac']
        return self.extension().lower() in audio_extensions
    
    def get_file_type_icon(self):
        """Get an appropriate Font Awesome icon for the file type"""
        if self.is_image():
            return "fa-image"
        elif self.is_document():
            if self.extension().lower() in ['pdf']:
                return "fa-file-pdf"
            elif self.extension().lower() in ['doc', 'docx', 'odt']:
                return "fa-file-word"
            elif self.extension().lower() in ['xls', 'xlsx']:
                return "fa-file-excel"
            elif self.extension().lower() in ['ppt', 'pptx']:
                return "fa-file-powerpoint"
            else:
                return "fa-file-alt"
        elif self.is_video():
            return "fa-file-video"
        elif self.is_audio():
            return "fa-file-audio"
        elif self.extension().lower() in ['zip', 'rar', '7z', 'tar', 'gz']:
            return "fa-file-archive"
        elif self.extension().lower() in ['html', 'css', 'js', 'py', 'java', 'c', 'cpp', 'php']:
            return "fa-file-code"
        else:
            return "fa-file"

class FileVersion(models.Model):
    """Model for storing file versions"""
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='versions')
    version_file = models.FileField(upload_to=get_file_path)
    version_size = models.BigIntegerField(default=0)  # Size in bytes
    version_number = models.PositiveIntegerField()
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='file_versions')
    
    class Meta:
        ordering = ['-version_number']
        unique_together = ('file', 'version_number')
    
    def __str__(self):
        return f"{self.file.title} - v{self.version_number}"
    
    def get_readable_file_size(self):
        """Convert file size to readable format (KB, MB, GB)"""
        return FileItem.get_readable_size(self.version_size)
    
    def extension(self):
        return os.path.splitext(self.version_file.name)[1][1:].upper()
    
    def filename(self):
        return os.path.basename(self.version_file.name)
    
    @classmethod
    def create_version(cls, file_item, version_file, user=None):
        """Create a new version for a file item"""
        # Get the latest version number
        latest_version = cls.objects.filter(file=file_item).order_by('-version_number').first()
        version_number = 1
        
        if latest_version:
            # If there are existing versions, set all to not current
            file_item.versions.update(is_current=False)
            version_number = latest_version.version_number + 1
        
        # Create new version
        version = cls(
            file=file_item,
            version_file=version_file,
            version_size=version_file.size,
            version_number=version_number,
            is_current=True,
            created_by=user or file_item.user
        )
        version.save()
        return version

class SharedFile(models.Model):
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='shared_with')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_files')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_files')
    access_level = models.CharField(max_length=10, choices=[
        ('view', 'View'),
        ('edit', 'Edit'),
        ('comment', 'Comment'),  # New access level for commenting only
    ], default='view')
    shared_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this share expires (optional)")
    
    class Meta:
        unique_together = ('file', 'shared_with')
        
    def __str__(self):
        return f"{self.file.title} shared with {self.shared_with.username}"
    
    def is_expired(self):
        """Check if the share has expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

class SharedFolder(models.Model):
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='shared_with')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_folders')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_folders')
    access_level = models.CharField(max_length=10, choices=[
        ('view', 'View'),
        ('edit', 'Edit'),
        ('comment', 'Comment'),  # New access level for commenting only
    ], default='view')
    shared_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this share expires (optional)")
    
    class Meta:
        unique_together = ('folder', 'shared_with')
        
    def __str__(self):
        return f"{self.folder.name} shared with {self.shared_with.username}"
    
    def is_expired(self):
        """Check if the share has expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

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

# New models for Collaboration Tools

class Comment(models.Model):
    """Model for storing comments on files"""
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.file.title}"
    
    def get_replies(self):
        """Get all replies to this comment"""
        return self.replies.all()

class CollaborationSession(models.Model):
    """Model for tracking real-time collaboration sessions"""
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='collaboration_sessions')
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    content = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Collaboration on {self.file.title}"
    
    def end_session(self):
        """End the collaboration session"""
        self.active = False
        self.ended_at = timezone.now()
        self.save()
    
    def add_participant(self, user):
        """Add a participant to the collaboration session"""
        participant, created = CollaborationParticipant.objects.get_or_create(
            session=self, 
            user=user,
            defaults={'is_active': True}
        )
        
        if not created and not participant.is_active:
            participant.is_active = True
            participant.save()

class CollaborationParticipant(models.Model):
    """Model for tracking participants in a collaboration session"""
    session = models.ForeignKey(CollaborationSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaboration_sessions')
    joined_at = models.DateTimeField(default=timezone.now)
    last_active = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    cursor_position = models.JSONField(null=True, blank=True)
    
    class Meta:
        unique_together = ('session', 'user')
    
    def __str__(self):
        return f"{self.user.username} in session on {self.session.file.title}"
    
    def update_activity(self):
        """Update the last active timestamp"""
        self.last_active = timezone.now()
        self.save()

class AuditLog(models.Model):
    """Model for tracking system actions for security and audit purposes"""
    ACTION_TYPES = (
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('share', 'Share'),
        ('unshare', 'Unshare'),
        ('download', 'Download'),
        ('upload', 'Upload'),
        ('collaborate', 'Collaborate'),
        ('admin', 'Admin Action'),
        ('security', 'Security Event'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    timestamp = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    object_type = models.CharField(max_length=255, blank=True, null=True)
    object_id = models.CharField(max_length=255, blank=True, null=True)
    details = models.JSONField(null=True, blank=True)
    success = models.BooleanField(default=True)
    
    # For linking to specific objects (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_pk = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_pk')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{username} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @classmethod
    def log(cls, action, user=None, request=None, obj=None, details=None, success=True):
        """Helper method to log an action"""
        try:
            log_entry = cls(
                user=user,
                action=action,
                success=success,
                details=details or {}
            )
            
            if request:
                log_entry.ip_address = cls.get_client_ip(request)
                log_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')
                
            if obj:
                log_entry.object_type = obj.__class__.__name__
                log_entry.object_id = str(obj.pk)
                log_entry.content_type = ContentType.objects.get_for_model(obj)
                log_entry.object_pk = obj.pk
                
            log_entry.save()
            return log_entry
        except Exception as e:
            # Fail silently - we never want logging to break functionality
            print(f"Error creating audit log: {str(e)}")
            return None
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request object"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

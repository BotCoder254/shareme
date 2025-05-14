from django.contrib import admin
from .models import FileItem, FileCategory, SharedFile, Folder, SharedFolder, FileShareLink
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse

class FolderHierarchyFilter(admin.SimpleListFilter):
    title = 'folder hierarchy'
    parameter_name = 'parent'
    
    def lookups(self, request, model_admin):
        return [('root', 'Root Folders')] + [(folder.id, folder.name) for folder in Folder.objects.filter(parent__isnull=True)]
    
    def queryset(self, request, queryset):
        if self.value() == 'root':
            return queryset.filter(parent__isnull=True)
        elif self.value():
            return queryset.filter(parent__id=self.value())
        return queryset

@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_icon', 'display_color', 'file_count')
    search_fields = ('name',)
    
    def display_icon(self, obj):
        return format_html('<i class="fas fa-{}" style="color: {}"></i> {}', 
                         obj.icon, obj.color, obj.icon)
    display_icon.short_description = "Icon"
    
    def display_color(self, obj):
        return format_html('<span style="background-color: {}; padding: 5px 10px; border-radius: 3px; color: white;">{}</span>', 
                         obj.color, obj.color)
    display_color.short_description = "Color"
    
    def file_count(self, obj):
        return FileItem.objects.filter(category=obj).count()
    file_count.short_description = "Files"

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'parent', 'file_count', 'subfolder_count', 'created_at')
    list_filter = ('created_at', FolderHierarchyFilter, 'user')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['move_to_root']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    
    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = "Files"
    
    def subfolder_count(self, obj):
        return obj.subfolders.count()
    subfolder_count.short_description = "Subfolders"
    
    def move_to_root(self, request, queryset):
        updated = queryset.update(parent=None)
        self.message_user(request, f"{updated} folders moved to root level.")
    move_to_root.short_description = "Move selected folders to root level"

class FileItemCategoryFilter(admin.SimpleListFilter):
    title = 'category'
    parameter_name = 'category'
    
    def lookups(self, request, model_admin):
        return [(category.id, category.name) for category in FileCategory.objects.all()]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category__id=self.value())
        return queryset

@admin.register(FileItem)
class FileItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'folder', 'category_display', 'file_size_display', 'is_favorite', 'is_public', 'created_at')
    list_filter = ('category', 'is_favorite', 'is_public', 'created_at', 'user')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('file_size', 'created_at', 'updated_at', 'file_preview')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'user', 'file')
        }),
        ('Display', {
            'fields': ('file_preview', 'category')
        }),
        ('Storage', {
            'fields': ('file_size', 'folder')
        }),
        ('Options', {
            'fields': ('is_favorite', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    
    def file_size_display(self, obj):
        return obj.get_readable_file_size()
    file_size_display.short_description = "Size"
    
    def category_display(self, obj):
        if obj.category:
            return format_html('<i class="fas fa-{}" style="color: {}"></i> {}', 
                             obj.category.icon, obj.category.color, obj.category.name)
        return "-"
    category_display.short_description = "Category"
    
    def file_preview(self, obj):
        if obj.extension().lower() in ['jpg', 'jpeg', 'png', 'gif']:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.file.url)
        return format_html('<i class="fas fa-file text-primary-500 text-4xl"></i>')
    file_preview.short_description = "Preview"

@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'shared_by', 'shared_with', 'access_level', 'shared_at')
    list_filter = ('access_level', 'shared_at', 'shared_by')
    search_fields = ('file__title', 'shared_by__username', 'shared_with__username')
    actions = ['revoke_access']
    
    def revoke_access(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Revoked access for {count} shared files.")
    revoke_access.short_description = "Revoke access for selected shared files"

@admin.register(SharedFolder)
class SharedFolderAdmin(admin.ModelAdmin):
    list_display = ('folder', 'shared_by', 'shared_with', 'access_level', 'shared_at')
    list_filter = ('access_level', 'shared_at', 'shared_by')
    search_fields = ('folder__name', 'shared_by__username', 'shared_with__username')
    actions = ['revoke_access']
    
    def revoke_access(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Revoked access for {count} shared folders.")
    revoke_access.short_description = "Revoke access for selected shared folders"

@admin.register(FileShareLink)
class FileShareLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_item_name', 'created_by', 'short_uuid', 'created_at', 'expires_status', 'access_count', 'max_access_count', 'is_valid', 'is_password_protected')
    list_filter = ('created_at', 'created_by')
    readonly_fields = ('uuid', 'created_at', 'access_count', 'share_link_url')
    search_fields = ('file__title', 'folder__name', 'created_by__username')
    fieldsets = (
        (None, {
            'fields': ('file', 'folder', 'created_by')
        }),
        ('Link Details', {
            'fields': ('uuid', 'share_link_url')
        }),
        ('Access Control', {
            'fields': ('expires_at', 'password', 'access_count', 'max_access_count')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    actions = ['reset_access_count', 'clear_expiration', 'delete_expired']
    
    def get_item_name(self, obj):
        """Get the name of the shared file or folder"""
        if obj.file:
            return format_html('<a href="{}">{}</a>', 
                            reverse('admin:files_fileitem_change', args=[obj.file.id]), 
                            f"File: {obj.file.title}")
        if obj.folder:
            return format_html('<a href="{}">{}</a>', 
                            reverse('admin:files_folder_change', args=[obj.folder.id]), 
                            f"Folder: {obj.folder.name}")
        return "Unknown"
    get_item_name.short_description = "Shared Item"
    
    def short_uuid(self, obj):
        return str(obj.uuid)[:8] + "..."
    short_uuid.short_description = "UUID"
    
    def expires_status(self, obj):
        if not obj.expires_at:
            return format_html('<span style="color: green;">Never expires</span>')
        elif obj.expires_at > timezone.now():
            days_left = (obj.expires_at - timezone.now()).days
            return format_html('<span style="color: orange;">Expires in {} days</span>', days_left)
        else:
            return format_html('<span style="color: red;">Expired</span>')
    expires_status.short_description = "Expiration"
    
    def is_password_protected(self, obj):
        return obj.password is not None
    is_password_protected.boolean = True
    is_password_protected.short_description = "Password Protected"
    
    def share_link_url(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.get_absolute_url(), obj.get_absolute_url())
    share_link_url.short_description = "Share Link"
    
    def reset_access_count(self, request, queryset):
        queryset.update(access_count=0)
        self.message_user(request, f"Access count reset for {queryset.count()} links.")
    reset_access_count.short_description = "Reset access count to zero"
    
    def clear_expiration(self, request, queryset):
        queryset.update(expires_at=None)
        self.message_user(request, f"Expiration removed for {queryset.count()} links.")
    clear_expiration.short_description = "Remove expiration date"
    
    def delete_expired(self, request, queryset):
        expired = queryset.filter(expires_at__lt=timezone.now()).count()
        queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f"Deleted {expired} expired links.")
    delete_expired.short_description = "Delete expired links"

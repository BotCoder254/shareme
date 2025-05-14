from django.contrib import admin
from .models import FileItem, FileCategory, SharedFile, Folder, SharedFolder, FileShareLink, FileVersion, Comment, CollaborationSession, CollaborationParticipant
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse, path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.template.response import TemplateResponse

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
    list_display = ('title', 'user', 'folder', 'category_display', 'file_size_display', 'is_favorite', 'is_public', 'version_count', 'in_trash', 'created_at')
    list_filter = ('category', 'is_favorite', 'is_public', 'created_at', 'user', 'deleted_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('file_size', 'created_at', 'updated_at', 'file_preview', 'version_history')
    actions = ['move_to_trash', 'restore_from_trash', 'permanent_delete']
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
            'fields': ('is_favorite', 'is_public', 'deleted_at')
        }),
        ('Versions', {
            'fields': ('version_history',),
            'classes': ('collapse',)
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
    
    def version_count(self, obj):
        return obj.get_version_count()
    version_count.short_description = "Versions"
    
    def in_trash(self, obj):
        return obj.is_in_trash()
    in_trash.boolean = True
    in_trash.short_description = "In Trash"
    
    def version_history(self, obj):
        versions = obj.versions.all()
        if not versions:
            return "No versions available"
        
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Version</th>'
        html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Created</th>'
        html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Size</th>'
        html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">User</th>'
        html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Current</th></tr>'
        
        for version in versions:
            html += f'<tr style="background-color: {"#f2f2f2" if version.is_current else "white"}">'
            html += f'<td style="border: 1px solid #ddd; padding: 8px;">v{version.version_number}</td>'
            html += f'<td style="border: 1px solid #ddd; padding: 8px;">{version.created_at.strftime("%Y-%m-%d %H:%M")}</td>'
            html += f'<td style="border: 1px solid #ddd; padding: 8px;">{version.get_readable_file_size()}</td>'
            html += f'<td style="border: 1px solid #ddd; padding: 8px;">{version.created_by.username if version.created_by else "Unknown"}</td>'
            html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{"✓" if version.is_current else "✗"}</td>'
            html += '</tr>'
        
        html += '</table>'
        return format_html(html)
    version_history.short_description = "Version History"
    
    def move_to_trash(self, request, queryset):
        for obj in queryset:
            obj.soft_delete()
        count = queryset.count()
        self.message_user(request, f"{count} file{'s' if count > 1 else ''} moved to trash.")
    move_to_trash.short_description = "Move selected files to trash"
    
    def restore_from_trash(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.is_in_trash():
                obj.restore()
                count += 1
        self.message_user(request, f"{count} file{'s' if count > 1 else ''} restored from trash.")
    restore_from_trash.short_description = "Restore selected files from trash"
    
    def permanent_delete(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.is_in_trash():
                # Update user storage before deleting
                if hasattr(obj.user, 'profile'):
                    profile = obj.user.profile
                    profile.storage_used = max(0, profile.storage_used - obj.file_size)
                    profile.save()
                obj.delete()
                count += 1
        self.message_user(request, f"{count} file{'s' if count > 1 else ''} permanently deleted.")
    permanent_delete.short_description = "Permanently delete selected files (from trash only)"

@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'file', 'version_number', 'file_size_display', 'is_current', 'created_at', 'created_by')
    list_filter = ('is_current', 'created_at', 'file__user')
    search_fields = ('file__title', 'created_by__username')
    readonly_fields = ('file', 'version_file', 'version_number', 'version_size', 'created_at', 'created_by')
    actions = ['set_as_current']
    
    def file_size_display(self, obj):
        return obj.get_readable_file_size()
    file_size_display.short_description = "Size"
    
    def set_as_current(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "Please select only one version to set as current.", level='error')
            return
            
        version = queryset.first()
        if version:
            # Set all versions of this file to not current
            FileVersion.objects.filter(file=version.file).update(is_current=False)
            # Set selected version as current
            version.is_current = True
            version.save()
            self.message_user(request, f"Version {version.version_number} set as current for file '{version.file.title}'.")
    set_as_current.short_description = "Set as current version"

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

# Add admin site header, title, and index title
admin.site.site_header = 'CloudVault Administration'
admin.site.site_title = 'CloudVault Admin'
admin.site.index_title = 'Administration'

# Register Collaboration models
@admin.register(CollaborationSession)
class CollaborationSessionAdmin(admin.ModelAdmin):
    list_display = ('file', 'started_by', 'active', 'created_at', 'ended_at')
    list_filter = ('active', 'created_at')
    search_fields = ('file__title', 'started_by__username')
    readonly_fields = ('created_at', 'ended_at')
    actions = ['end_sessions']
    
    def end_sessions(self, request, queryset):
        count = queryset.filter(active=True).update(active=False, ended_at=timezone.now())
        self.message_user(request, f"Ended {count} collaboration sessions.")
    end_sessions.short_description = "End selected collaboration sessions"

@admin.register(CollaborationParticipant)
class CollaborationParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'is_active', 'joined_at', 'last_active')
    list_filter = ('is_active', 'joined_at')
    search_fields = ('user__username', 'session__file__title')
    readonly_fields = ('joined_at', 'last_active')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'file', 'parent', 'created_at', 'updated_at')
    list_filter = ('created_at', 'user')
    search_fields = ('content', 'user__username', 'file__title')
    readonly_fields = ('created_at', 'updated_at')

# Create an admin action to run the cleanup_expired_shares management command
def run_cleanup_expired_shares(modeladmin, request, queryset):
    from django.core.management import call_command
    call_command('cleanup_expired_shares')
    modeladmin.message_user(request, "Expired shares cleanup completed successfully!", messages.SUCCESS)

run_cleanup_expired_shares.short_description = "Run cleanup for expired shares"

# Add the action to the appropriate admin models
SharedFileAdmin.actions += [run_cleanup_expired_shares]
SharedFolderAdmin.actions += [run_cleanup_expired_shares]

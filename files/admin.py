from django.contrib import admin
from .models import FileItem, FileCategory, SharedFile, Folder, SharedFolder, FileShareLink

@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color')
    search_fields = ('name',)

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

@admin.register(FileItem)
class FileItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'folder', 'category', 'file_size', 'is_favorite', 'is_public', 'created_at')
    list_filter = ('category', 'is_favorite', 'is_public', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('file_size', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'shared_by', 'shared_with', 'access_level', 'shared_at')
    list_filter = ('access_level', 'shared_at')
    search_fields = ('file__title', 'shared_by__username', 'shared_with__username')

@admin.register(SharedFolder)
class SharedFolderAdmin(admin.ModelAdmin):
    list_display = ('folder', 'shared_by', 'shared_with', 'access_level', 'shared_at')
    list_filter = ('access_level', 'shared_at')
    search_fields = ('folder__name', 'shared_by__username', 'shared_with__username')

@admin.register(FileShareLink)
class FileShareLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_item_name', 'created_by', 'created_at', 'expires_at', 'access_count', 'is_valid')
    list_filter = ('created_at',)
    readonly_fields = ('uuid', 'created_at', 'access_count')
    search_fields = ('file__title', 'folder__name', 'created_by__username')
    
    def get_item_name(self, obj):
        """Get the name of the shared file or folder"""
        if obj.file:
            return f"File: {obj.file.title}"
        if obj.folder:
            return f"Folder: {obj.folder.name}"
        return "Unknown"
    get_item_name.short_description = "Shared Item"
